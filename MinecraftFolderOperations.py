import os
import re


def process_filename(filename):
    # Remove unwanted characters and substrings
    cleaned = re.sub(r"[\[\]()]", "", filename)  # Remove brackets and parentheses, but not '+'
    cleaned = re.sub(r"\.jar$", "", cleaned)  # Remove .jar extension
    cleaned = re.sub(r"(neoforge|fabric)", "", cleaned, flags=re.IGNORECASE)  # Remove unwanted terms
    cleaned = re.sub(r"(?<=\d)(?:mc_?|mc-?|\+)?1\.21(?:\.1|\.X)?(?=$|[-_.+])|(?:^|[-_.+])(?:mc_?|mc-?|\+)?1\.21(?:\.1|\.X)?(?=$|[-_.+])", "", cleaned, flags=re.IGNORECASE)  # Remove Minecraft version references
    cleaned = re.sub(r"\+", "", cleaned)  # Now remove '+' characters

    # Find potential split points
    split_matches = list(re.finditer(r"(?<=\d)[-_v]|[-_v](?=\d)|[-_]v(?=\d)", cleaned))

    if not split_matches:
        return cleaned + ": unknown"

    # Find the most relevant split point
    best_split = max(split_matches, key=lambda m: len(re.findall(r"\d", cleaned[m.end():])))
    split_point = best_split.start()

    # Split and clean parts
    part1 = cleaned[:split_point].strip("-_ ")
    part2 = cleaned[split_point:].strip("-_ ")

    # Determine which part is the name and which is the version
    if re.search(r"\d", part1) and not re.search(r"\d", part2):
        name_part, version_part = part2, part1
    else:
        name_part, version_part = part1, part2

    return name_part, version_part


def process_folders(main_folder, update_folder):
    output_file = os.path.join(main_folder, "processed_mods.txt")
    mod_versions = {}

    # Process main folder
    for filename in os.listdir(main_folder):
        if not filename.endswith(".jar"):  # Ignore non-.jar files
            continue
        name, version = process_filename(filename)
        mod_versions[name] = version  # Store version from main folder

    with open(output_file, "w") as f:
        # Process update folder
        for filename in os.listdir(update_folder):
            if not filename.endswith(".jar"):  # Ignore non-.jar files
                continue
            name, new_version = process_filename(filename)

            if name in mod_versions and mod_versions[name] != new_version:
                f.write(f"{name}: {mod_versions[name]} -> {new_version}\n")  # Version changed
            else:
                f.write(f"{name}: {new_version} new\n")  # New mod or same version

        # Write remaining mods from the main folder that weren't updated
        for name, version in mod_versions.items():
            if name not in [process_filename(f)[0] for f in os.listdir(update_folder) if f.endswith(".jar")]:
                f.write(f"{name}: {version}\n")

    print(f"Processed filenames saved to {output_file}")

def compare_versions(v1, v2):
    """Compares two version strings and returns:
       - 1 if v1 is greater,
       - -1 if v2 is greater,
       - 0 if they are equal.
    """
    v1_parts = [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', v1)]
    v2_parts = [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', v2)]
    
    return (v1_parts > v2_parts) - (v1_parts < v2_parts)

def delete_duplicate_mods(folder):
    mod_files = {}
    mods_removed = []

    for filename in os.listdir(folder):
        if not filename.endswith(".jar"):  # Ignore non-.jar files
            continue

        name, version = process_filename(filename)
        file_path = os.path.join(folder, filename)

        if name in mod_files:
            existing_version, existing_path = mod_files[name]

            if compare_versions(version, existing_version) > 0:
                mods_removed.append(name + " " + existing_version)
                os.remove(existing_path)  # Remove the lesser version
                mod_files[name] = (version, file_path)  # Keep the higher version
            else:
                mods_removed.append(name + " " + version)
                os.remove(file_path)  # Remove the lesser version
        else:
            mod_files[name] = (version, file_path)  # Store name-version mapping
    for mod in mods_removed:
        print(f"Removed duplicate mod: {mod}")
    print("Duplicate mods removed, keeping only the highest versions.")

def cleanup_names_given_list(files):
    newFiles=[]
    for filename in files:
        name, version = process_filename(filename)
        newFiles.append(f"{name}: {version}")
    return newFiles

def get_differences(folder1, folder2):
    output_file = os.path.join(folder1, "client_and_serverside_mods.txt")
    clientside_files = [f for f in os.listdir(folder1) if f.endswith(".jar")]
    serverside_files = [f for f in os.listdir(folder2) if f.endswith(".jar")]

    clientside_only = [f for f in clientside_files if f not in serverside_files]
    serverside_only = [f for f in serverside_files if f not in clientside_files]
    with open(output_file, "w") as f:
        f.write("Clientside only files:\n")
        clientside_only = cleanup_names_given_list(clientside_only)
        f.write("\n".join(clientside_only))
        f.write("\n")
        f.write("\nServerside only files:\n")
        serverside_only = cleanup_names_given_list(serverside_only)
        f.write("\n".join(serverside_only))
    print(f"Clientside only files: {clientside_only}")
    print(f"Serverside only files: {serverside_only}")

    

if __name__ == "__main__":
    check_process = "0"
    while check_process == "0":
        check_process = input(
            "Select an option:\n"
            "1. Compare folders and update the version update file.\n"
            "2. Delete duplicate mods in the update folder.\n"
            "3. Find clientside and serverside-only files.\n"
            "4. Exit.\n"
        )

        if check_process not in {"1", "2", "3", "4"}:
            print("Press a number between 1 and 4 please.\n")
            check_process = "0"
                
        if check_process == "1":
            folder1 = input("Enter the main folder path: ")
            folder2 = input("Enter the updates folder path: ")
            process_folders(folder1, folder2)
        elif check_process == "2":
            folder = input("Enter the folder path: ")
            delete_duplicate_mods(folder)
        elif check_process == "3":
            folder1 = input("Enter the client folder path: ")
            folder2 = input("Enter the server folder path: ")
            get_differences(folder1, folder2)
        elif check_process == "4":
            print("Exiting...")
            break