import pypff
import re
import argparse
import json
from tqdm import trange

missed_lines = []


def extract_to_from_info(msg) -> tuple[str, str]:
    """Extract sender and recipient from transport headers. -> returns (sender, recipient)"""

    transport_headers = msg.transport_headers
    id_str = str(msg.identifier)

    if not transport_headers:
        return "error_transport", "error_transport"

    regex = lambda line: re.search(r"<?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})>?", line)
    split = transport_headers.split("\r\n")

    sender = None
    recipient = None
    for line in split:
        if sender and recipient:
            return sender, recipient

        if line.startswith("To: "):
            recipient = regex(line)
            if recipient is None:
                missed_lines.append(line)
                # raise AttributeError("invalid recipient: " + line)
                recipient = "recipient_not_found:" + id_str
            else:
                recipient = recipient.group(1)

        elif line.startswith("From: "):
            sender = regex(line)
            if sender is None:
                missed_lines.append(line)
                # raise AttributeError("invalid sender: " + line)
                sender = "sender_nit_found:" + id_str
            else:
                sender = sender.group(1)

    error = "missing: "
    if not sender and not recipient:
        error += "sender and recipient"
    elif not sender:
        error += "sender"
    elif not recipient:
        error += "recipient"
    raise AttributeError("missing: " + error)


def process_folder(folder, result_dict):

    for i in trange(folder.number_of_sub_messages,
                    desc="processing folder: " + folder.name):

        msg = folder.get_sub_message(i)
        s_date = msg.delivery_time

        sender, recipient = extract_to_from_info(msg)

        # recipient level creation if not exist
        if recipient not in result_dict:
            result_dict[recipient] = {}

        # sender level creation if not exist
        if sender not in result_dict[recipient]:
            result_dict[recipient][sender] = {
                "n_mails": 0,
                "dates": []
            }

        # update
        result_dict[recipient][sender]["n_mails"] += 1
        result_dict[recipient][sender]["dates"].append(s_date.isoformat())


def iterate_folders(root, result_dict):
    for sub in root.sub_folders:
        if sub.number_of_sub_messages > 0:
            process_folder(sub, result_dict)
        iterate_folders(sub, result_dict)


def extract_info(pst_path: str):
    pst = pypff.file()
    pst.open(pst_path)

    try:
        root = pst.get_root_folder()
        extract_dic = {}
        iterate_folders(root, extract_dic)

    finally:
        pst.close()

    return extract_dic


def save_to_json(extract_dic, output_path: str):
    with open(output_path, "w") as f:
        json.dump(extract_dic, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Parse a PST and aggregate unique senders per delivered alias.")
    parser.add_argument("pst", help="Path to the .pst file")
    parser.add_argument("--json_out", "-jo", help="Write output to JSON file path (e.g. out.json).")
    parser.add_argument("--console_out", "-co", action="store_true", help="Print pretty JSON output to console.")

    args = parser.parse_args()

    if not args.json_out and not args.console_out:
        parser.error("You must specify at least one output option: --json_out/-jo and/or --console_out/-co")


    extract = extract_info(args.pst)
    print("missed lines:")
    print(missed_lines)

    if args.console_out:
        print(json.dumps(extract, ensure_ascii=False, indent=2, sort_keys=True))

    if args.json_out:
        save_to_json(extract, args.json_out)

if __name__ == "__main__":
    main()