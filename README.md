# WhoMailedMe - WMM

## Extracting sender email addresses from an .PST file

A simple script that breaks down the email addresses of senders by recipient email and outputs them
as JSON in a file and/or in the console.

This is helpful to see which 

### Features:
- extract sender email addresses from .PST file
- number of mails send from each sender
- dates of mails send from each sender
- broken down by recipient email
- output JSON:
```JSON
{
  "receiver@example.com": {
    "sender@example.com": {
      "n_mails": 42,
      "dates": [
        "2025-02-20T16:48:49",
        "2025-03-01T09:12:11"
      ]
    }
  }
}
```

### Planned features:
- print simply all sender email addresses to console / file


## Usage:

```
python wmm.py <path_to_pst_file> [-jo <output_json_file>] [-co] [-so]
```

**At least one of the three output format flags must be specified:**
- `-jo` specifies the output JSON file.
- `-co` prints the JSON to the console.
- `-so` prints a simple list of sender email addresses to the console.

`-co` and `-so` are mutually exclusive.

run `python3 wmm.py -h` for help

## Known issues:
- sometimes the transport header differs from the expected format. -> leads to unknown senders / receivers.
- sometimes transporter header is missing completely.

# Licensing
Permission is granted to use, copy and modify this software for non-commercial purposes only.
Commercial use requires explicit written permission from the author.