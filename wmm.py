import pypff
import re
import argparse
import json
from tqdm import trange

missed_lines = [] # collects lines which started with "To:" or "From:" but didn't match regex


def parse_transport_header(msg) -> tuple[str, str]:
    """
    Extract sender and recipient from transport headers.

    This function parses the transport headers contained in the provided
    pypff message object, extracts the email addresses for both the sender and
    the recipient, and returns them as a tuple. If the transport headers
    are missing or invalid, appropriate default error strings are returned
    for the sender and recipient. The function raises an exception if either
    or both are missing after processing the headers.

    :param msg: A pypff message object that contains transport headers and
        an identifier used to derive default error strings when sender
        or recipient cannot be determined
    :return: A tuple containing the sender's email address as the first
        element and the recipient's email address as the second element
        (sender, recipient)
    """

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
            else:
                recipient = recipient.group(1)

        elif line.startswith("From: "):
            sender = regex(line)
            if sender is None:
                missed_lines.append(line)
            else:
                sender = sender.group(1)

    if sender is None:
        sender = "sender_not_found:" + id_str

    if recipient is None:
        recipient = "recipient_not_found:" + id_str

    return sender, recipient


def process_folder(folder, result_dict):
    """
    Processes a given folder of messages to extract communication data and populates
    the provided result dictionary with recipient and sender information. The function
    analyzes each message in the folder and aggregates the number of messages and their
    corresponding delivery times for each sender-recipient pair.

    :param folder: The pypff folder object containing sub-messages to process.
    :param result_dict: A dictionary to store the aggregated results. The structure of this
        dictionary is:

        {
            recipient (str): {
                sender (str): {
                    "n_mails": int,  # Number of messages from sender to recipient
                    "dates": List[str]  # List of ISO 8601 format dates for messages
                }
            }
        }

    :return: Side effect: updates the result_dict parameter with the aggregated data.
    """

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
    """
    Recursively iterates through folders and processes each folder with messages.

    :param root: The pypff root folder to start the traversal.
    :param result_dict: A dictionary to store processed information for folders
        with messages. This dictionary is updated by the `process_folder` function
        during traversal.
    :return: Side effect: updates the result_dict parameter with the aggregated data.
    """
    for sub in root.sub_folders:
        if sub.number_of_sub_messages > 0:
            process_folder(sub, result_dict)
        iterate_folders(sub, result_dict)


def extract_info(pst_path: str):
    """
    Extracts information from a PST (Personal Storage Table) file and organizes it into a dictionary.

    This function reads the structure of a PST file provided by the user and processes its
    contents into a dictionary format for further use.

    The generated dictionary has the following structure:
        {
            recipient (str): {
                sender (str): {
                    "n_mails": int,  # Number of messages from sender to recipient
                    "dates": List[str]  # List of ISO 8601 format dates for messages
                }
            }
        }

    :param pst_path: The file path to the PST file that is to be processed.
    :return: A dictionary containing extracted information from the PST file.
    """
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
    """
    Saves the provided dictionary to a JSON file at the specified path.

    :param extract_dic: Dictionary to be serialized and written to a JSON file.
                        This contains key-value pairs that will form the JSON content.
    :param output_path: The file path where the JSON content will be saved.
    :return: None
    """
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

    if args.console_out:
        print(json.dumps(extract, ensure_ascii=False, indent=2, sort_keys=True))

    if args.json_out:
        save_to_json(extract, args.json_out)

if __name__ == "__main__":
    main()