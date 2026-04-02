from tqdm import tqdm
import json

messages = []

with open("messages.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)
    for entry in tqdm(dataset, desc='Processing dataset'):
        if entry["Contents"] is not None and entry["Contents"] != "":
            messages.append(entry["Contents"])

with open("messages.txt", "w", encoding="utf-8") as f:
    for message in tqdm(messages, desc="Writing messages to file"):
        f.write(message + "\n")
