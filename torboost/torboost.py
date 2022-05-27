from urllib import parse
import argparse
import hashlib
import logging
import pathlib
import queue
import requests
import shutil
import stem.process
import threading
import urllib3.exceptions


__version__ = '0.9.1'


logging.basicConfig(format='%(name)s %(levelname)s [%(asctime)s] %(message)s', level=logging.INFO)
logger = logging.getLogger('torboost')


class TorBoost:

    WORKERS_DIR = 'workers'
    WORKER_PREFIX = 'torboost-'
    DOWNLOADS_DIR = 'downloads'

    def __init__(self, args):
        self.args = args
        self.procs = dict()
        self.content_size = None
        self.queue = queue.Queue()
        self.workers = list()
        self.url_hash = hashlib.sha256(self.args.url.encode('ascii')).hexdigest()
        self.output_dir = pathlib.Path(self.DOWNLOADS_DIR, self.url_hash)
        pathlib.Path(self.WORKERS_DIR).mkdir(parents=True, exist_ok=True)

    def print_bootstrap(self, line):
        if 'Bootstrapped ' in line:
            logger.info(line)

    def request(self, headers, socks_port):
        headers.update({
            'User-Agent': self.args.user_agent    
        })
        proxies = {
            'http': f'socks5h://localhost:{socks_port}',
            'https': f'socks5h://localhost:{socks_port}',
        }
        return requests.get(self.args.url, headers=headers, proxies=proxies, stream=True)

    def worker(self):
        name = threading.current_thread().name
        while True:
            chunk, proc_no = self.queue.get()
            output = self.output_dir / f'{chunk[0]}-{chunk[1]}.chunk'
            expected_size = chunk[1] - chunk[0] + 1
            if output.is_file() and output.stat().st_size == expected_size:
                output_size = output.stat().st_size
                logger.debug(f'Chunk {chunk} already exists (size: {output_size}), skipping')
                self.queue.task_done()
                continue
            proc_config = self.procs[proc_no]
            socks_port = proc_config['SocksPort']
            headers = {'Range': f'bytes={chunk[0]}-{chunk[1]}'}
            logger.debug(f'Worker [{name}] is requesting chunk {chunk}')
            failed = False
            try:
                response = self.request(headers, socks_port)
                logger.debug(f'Response headers for {chunk}: {response.headers}')
            except requests.exceptions.ConnectionError:
                logger.debug(f'Worker [{name}] failed on connect, putting chunk {chunk} back to the queue')
                failed = True
            else:
                logger.info(f'Worker [{name}] is downloading chunk {chunk}')
                try:
                    with open(str(output), 'wb') as fil:
                        fil.write(response.raw.read())
                    output_size = output.stat().st_size
                    if output_size != expected_size:
                        logger.debug(f'Invalid chunk size ({output_size}, expected: {expected_size}) for {chunk}, putting it back to the queue')
                        failed = True
                except urllib3.exceptions.ProtocolError:
                    logger.debug(f'Worker [{name}] failed on read, putting chunk {chunk} back to the queue')
                    failed = True
                else:
                    if not failed:
                        logger.info(f'Worker [{name}] saved chunk {chunk}')
            if failed:
                self.queue.put((chunk, int(name)))
            self.queue.task_done()

    def tor_proc(self, proc_no):
        data_dir = pathlib.Path(self.WORKERS_DIR, self.WORKER_PREFIX + str(proc_no))
        socks_port = self.args.socks_port_start + proc_no
        control_port = self.args.control_port_start + proc_no
        config = {
            'SocksPort': str(socks_port),
            'ControlPort': str(control_port),
            'DataDirectory': str(data_dir),
        }
        logger.info(f'Bootstrapping Tor process {proc_no}')
        logger.debug(f'with config: {config}')
        proc = stem.process.launch_tor_with_config(
            take_ownership=True,
            config = config,
            timeout=self.args.timeout,
            init_msg_handler = self.print_bootstrap,
        )
        self.procs[proc_no] = config
        self.procs[proc_no]['process'] = proc

    def combine(self):
        logger.info(f'Combining...')
        files = sorted([
            fil for fil in pathlib.os.listdir(self.output_dir) if fil.endswith('.chunk')
        ], key=lambda x: int(x.split('-')[0]))
        orig_name = pathlib.posixpath.basename(
            parse.unquote(parse.urlparse(self.args.url).path)
        )
        output_path = pathlib.Path(self.DOWNLOADS_DIR, orig_name)
        if output_path.exists():
            output_path.unlink()
        with open(output_path, 'ab') as dest_file:
            for fil in files:
                with open(self.output_dir / fil, 'rb') as inp:
                    shutil.copyfileobj(inp, dest_file)
        logger.info(f'Saved: {orig_name} to {self.DOWNLOADS_DIR}')

    def connect(self):
        for proc_no in range(self.args.tor_processes):
            self.tor_proc(proc_no)

    def start(self):
        if not self.content_size:
            raise RuntimeError('TorBoost.content_size must be set first!')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f'Chunks are being saved in {self.output_dir}')

        chunks = list()
        chunk_no = int(self.content_size / self.args.chunk_size)
        for i in range(0, chunk_no):
            chunk_start = i * self.args.chunk_size
            chunk_end = chunk_start + self.args.chunk_size
            chunks.append((chunk_start, chunk_end - 1))
        chunks.append((chunk_end, self.content_size - 1))

        for idx, chunk in enumerate(chunks, start=1):
            self.queue.put((chunk, (self.args.tor_processes - 1) % idx))

        # NOTE: Same number of workers as there are Tor sockets
        for worker in range(self.args.tor_processes):
            thread = threading.Thread(name=str(worker), target=self.worker, daemon=True)
            thread.start()
            self.workers.append(thread)
        self.queue.join()
        self.combine()


def entry_point():
    default_headers = requests.utils.default_headers()
    parser = argparse.ArgumentParser(
        description='Utility for downloading files from onion services using multiple Tor circuits',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-u', '--url', required=True, help='Download URL')
    parser.add_argument('-p', '--tor-processes', default=5, type=int, help='Number of Tor processes')
    parser.add_argument('--control-port-start', type=int, default=10080, help='First port for Tor control')
    parser.add_argument('--socks-port-start', type=int, default=9080, help='First port for SOCKS')
    parser.add_argument('--timeout', default=300, help='Timeout for Tor relay connection')
    parser.add_argument('--chunk-size', default=50000000, help='Size of a single download block (in bytes)')
    parser.add_argument('--user-agent', default=default_headers['User-Agent'], help='User-Agent header')
    parser.add_argument('--debug', action='store_const', dest='loglevel', const=logging.DEBUG, default=logging.INFO, help='Enable debugging mode (verbose output)')
    parser.add_argument('--combine', action='store_true', help='Combine all chunks downloaded so far')
    args = parser.parse_args()
    logger.setLevel(args.loglevel)
    boost = TorBoost(args)
    if args.combine:
        boost.combine()
        exit()
    boost.connect()
    # NOTE: Do NOT use HEAD here, leads to inconsistent results
    response = boost.request({'Accept-Encoding': 'identity'}, boost.procs[0]['SocksPort'])
    logger.debug(f'Initial response headers: {response.headers}')
    boost.content_size = int(response.headers['Content-Length'])
    logger.info(f'Download size: {boost.content_size}')
    boost.start()


if __name__ == '__main__':
    entry_point()
