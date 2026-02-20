# WhoMailedMe - WMM

## Extracting sender email addresses from an .PST file

A simple script that breaks down the email addresses of senders by recipient email and outputs them
as JSON in a file and/or in the console.

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
python wmm.py <path_to_pst_file> [-jo <output_json_file>] [-co]
```

**At least one of the two output format flags must be specified:**
- `-jo` specifies the output JSON file.
- `-co` prints the JSON to the console.

run `python3 wmm.py -h` for help

## Known issues:
- sometimes the transport header differs from the expected format. -> leads to unknown senders / receivers.
- sometimes transporter header is missing completely.