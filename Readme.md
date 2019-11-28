Query the list of international conferences in astronomy and astrophysics, store them locally and highlight the recently annouced ones.

![List of conferences](/screenshot.png?raw=true "Screenshot")

# Install
Clone the repository, install the requirements and run `conferences.py`. 
```
git clone https://github.com/cphyc/conferences.git
cd conferences
pip install -r Requirements.txt
```

# Options

```
usage: conferences.py [-h] [-u] [-f START [START ...]] [-t END [END ...]] [-s]

Interact with conferences from conference-service.com

optional arguments:
  -h, --help            show this help message and exit
  -u, --update          Update database.
  -f START [START ...], --from START [START ...]
                        Earliest date when printing (default: now).
  -t END [END ...], --to END [END ...]
                        Latest date when printing.
  -s, --silent          Do not print conferences.
```
Note that you the input format for `-f` and `-t` is *very* flexible. It accepts human-formatted, including for example `--to next year`, `--from 31 Dec. 2019`, etc. It relies on the awesome https://github.com/scrapinghub/dateparser for this.

