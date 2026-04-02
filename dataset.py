import os

from tqdm import tqdm
import json

messages: list[str] = []


def main() -> None:
    for root, _, files in os.walk("Messages"):
        for file in tqdm(files, desc="Iterating over files...", unit="file"):
            if file == "messages.json":
                print("\nDoing file: " + os.path.join(root, file))
                with open("messages.json", "r", encoding="utf-8") as f:
                    dataset = json.load(f)
                    for entry in dataset:
                        message: str = entry["Contents"] or ""
                        if message != "":
                            messages.append(message)

    with open("messages.txt", "w", encoding="utf-8") as f:
        if messages != []:
            for message in tqdm(messages, desc="Writing messages to file"):
                f.write(message + "\n")
        else:
            raise ValueError(
                "You must have a non-empty list of messages in order for markovbot to work.")


if __name__ == "__main__":
    main()
