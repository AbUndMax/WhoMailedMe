import pypff
import re
import argparse
import json
from tqdm import trange

missed_log = {}  # collects lines which started with "To:" or "From:" but didn't match regex


def update_log(id_str, sender, recipient):
    """Update `missed_log` for a message id with the final `(sender, recipient)` tuple.

    If an entry for `id_str` exists in `missed_log`, the function adds/overwrites the
    key `final_tuple` with `(sender, recipient)`.
    """
    if log := missed_log.get(id_str):
        log["final_tuple"] = (sender, recipient)

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
            update_log(id_str, sender, recipient)
            return sender, recipient

        if line.startswith("To: "):
            recipient = regex(line)
            if recipient is None:
                missed_log[id_str] = {"recipient_missed": line}
            else:
                recipient = recipient.group(1)

        elif line.startswith("From: "):
            sender = regex(line)
            if sender is None:
                missed_log[id_str] = {"sender_missed": line}
            else:
                sender = sender.group(1)

    if sender is None:
        sender = "sender_not_found:" + id_str

    if recipient is None:
        recipient = "recipient_not_found:" + id_str

    update_log(id_str, sender, recipient)
    return sender, recipient


def process_folder(folder, result_dict, processing_folder, total_n_folders, longest_name_len):
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

    :return: number of processed folders
    :Side effect: updates the result_dict parameter with the aggregated data.
    """

    process_msg = f"processing folder {processing_folder:>{len(str(total_n_folders))}}/{total_n_folders} > "
    process_msg  += folder.name.ljust(longest_name_len + 1)

    for i in trange(folder.number_of_sub_messages,
                    desc= process_msg):

        msg = folder.get_sub_message(i)
        s_date = msg.delivery_time

        sender, recipient = parse_transport_header(msg)

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

    return processing_folder + 1


def calculate_process_info(root, total_folders_to_process: int = 0, longest_folder_name: int = 0) -> tuple[int, int]:
    """
    Calculate the total number of folders to process and the length of the longest folder name.

    This function recursively traverses the folder structure starting from the given root folder.
    Folders containing messages are counted, and the folder with the longest name is identified. The
    results include the total number of folders to process and the length of the longest folder name.

    :param root: The root pypff folder from which the traversal begins.
    :param total_folders_to_process: The initial count of folders with messages, defaulting to 0.
    :param longest_folder_name: The initial length of the longest folder name, defaulting to 0.
    :return: A tuple containing the total number of folders to process and the length of the longest
        folder name.
    """
    for sub in root.sub_folders:
        # Always recurse first so folders with messages deeper down are counted too
        total_folders_to_process, longest_folder_name = calculate_process_info(
            sub, total_folders_to_process, longest_folder_name
        )

        # Count this folder if it has messages
        if sub.number_of_sub_messages > 0:
            total_folders_to_process += 1
            longest_folder_name = max(longest_folder_name, len(sub.name))

    return total_folders_to_process, longest_folder_name


def iterate_folders(root, result_dict, total_folders_to_process, longest_folder_name, processing_folder=1):
    """
    Recursively iterates through folders and processes each folder with messages.

    :param root: The pypff root folder to start the traversal.
    :param result_dict: A dictionary to store processed information for folders
        with messages. This dictionary is updated by the `process_folder` function
        during traversal.
    :return: number of processed folders
    :Side effect: updates the result_dict parameter with the aggregated data.
    """

    for sub in root.sub_folders:
        processing_folder = iterate_folders(sub, result_dict, total_folders_to_process, longest_folder_name, processing_folder)
        if sub.number_of_sub_messages > 0:
            processing_folder = process_folder(sub, result_dict, processing_folder, total_folders_to_process, longest_folder_name)

    return processing_folder


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
        total_folders, longest_name = calculate_process_info(root)
        iterate_folders(root, extract_dic, total_folders, longest_name)

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
    # print(json.dumps(missed_log, ensure_ascii=False, indent=2, sort_keys=True))

    if args.console_out:
        print(json.dumps(extract, ensure_ascii=False, indent=2, sort_keys=True))

    if args.json_out:
        save_to_json(extract, args.json_out)

if __name__ == "__main__":
    main()