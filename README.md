# torboost

> Download utility for Tor

## About

This tool was designed specifically for downloading big files from onion services for analysis. It does so by retrieving chunks using multiple circuits, so the server must support byte ranges (`Accept-Ranges`, most of them do). If a given part fails (connection issues, chunk smaller than expected), it is being put back to the queue. Once all bits and pieces are ready they are combined, and the final result is saved in the `./downloads` directory.

## Warning

**This way of utilizing Tor network reduces your anonymity!**

## Requirements

* `tor`

## Installation

`$ pip install torboost`

## Usage

You may need to wait a while until all circuits are established:

`$ torboost -u 'http://example.onion/data.zip'`

If you want to combine the files before download is finished:

`$ torboost --combine -u 'http://example.onion/data.zip'`

### Arguments

```
usage: torboost [-h] -u URL [-p TOR_PROCESSES] [--control-port-start CONTROL_PORT_START] [--socks-port-start SOCKS_PORT_START] [--timeout TIMEOUT] [--chunk-size CHUNK_SIZE] [--user-agent USER_AGENT] [--debug]
                [--combine]

Utility for downloading files from onion services using multiple Tor circuits

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Download URL (default: None)
  -p TOR_PROCESSES, --tor-processes TOR_PROCESSES
                        Number of Tor processes (default: 5)
  --control-port-start CONTROL_PORT_START
                        First port for Tor control (default: 10080)
  --socks-port-start SOCKS_PORT_START
                        First port for SOCKS (default: 9080)
  --timeout TIMEOUT     Timeout for Tor relay connection (default: 300)
  --chunk-size CHUNK_SIZE
                        Size of a single download block (in bytes) (default: 50000000)
  --user-agent USER_AGENT
                        User-Agent header (default: python-requests/2.27.1)
  --debug               Enable debugging mode (verbose output) (default: INFO)
  --combine             Combine all chunks downloaded so far (default: False)
```