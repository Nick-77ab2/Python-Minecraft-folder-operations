import os
import re


def cleanup(filename):
    # Remove unwanted characters and substrings
    cleaned = re.sub(r"[\[\]()]", "", filename)  # Remove brackets and parentheses, but not '+'
    cleaned = re.sub(r"\.jar$", "", cleaned)  # Remove .jar extension
    cleaned = re.sub(r"(neo|neoforge|fabric)", "", cleaned, flags=re.IGNORECASE)  # Remove unwanted terms
    return cleaned

def process_filename(filename, minecraft_version):
    cleaned = cleanup(filename)
    major, minor = map(int, minecraft_version.split("."))  # Split into major and minor parts
    previous_minecraft_version = f"{major}.{minor - 1}"  # Decrease minor version
    cleaned = re.sub(rf"(?<=\d)(?:mc_?|mc-?|\+)?(?:{previous_minecraft_version}\.[1-9]-)?(?:{minecraft_version})(?:\.[1-9]+|\.X|x)?(?=$|[-_.+])|(?:^|[-_+])(?:mc_?|mc-?|\+)?(?:{previous_minecraft_version}\.[1-9]-)?(?:{minecraft_version})(?:\.[1-9]+|\.X|x)?(?=$|[-_.+])", "", cleaned, flags=re.IGNORECASE)
    #cleaned = re.sub(rf"(?<=\d)(?:mc_?|mc-?|\+)?{minecraft_version}(?:\.1|\.X)?(?=$|[-_.+])|(?:^|[-_.+])(?:mc_?|mc-?|\+)?{minecraft_version}(?:\.1|\.X)?(?=$|[-_.+])", "", cleaned, flags=re.IGNORECASE)  # Remove Minecraft version references
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


def process_folders(main_folder, update_folder, minecraft_version):
    output_file = os.path.join(main_folder, "processed_mods.txt")
    mod_versions = {}
    mods_updated = 0
    mods_new = 0

    # Process main folder
    for filename in os.listdir(main_folder):
        if not filename.endswith(".jar"):  # Ignore non-.jar files
            continue
        name, version = process_filename(filename, minecraft_version)
        mod_versions[name.lower()] = version  # Store version from main folder (keyed by lowercase name)

    with open(output_file, "w") as f:
        # Process update folder
        for filename in os.listdir(update_folder):
            if not filename.endswith(".jar"):  # Ignore non-.jar files
                continue

            name, new_version = process_filename(filename, minecraft_version)

            # Find the actual key in `mod_versions` that matches `name.lower()`
            matching_key = next((key for key in mod_versions if key == name.lower()), None)

            if matching_key and mod_versions[matching_key] != new_version:
                f.write(f"{matching_key}: {mod_versions[matching_key]} -> {new_version}\n")  # Version changed
                mods_updated += 1
            elif matching_key:  # Mod exists with the same version
                continue  # No need to count as a new mod
            else:
                f.write(f"{name}: {new_version} new\n")  # New mod
                mods_new += 1

        # Write remaining mods from the main folder that weren't updated
        existing_mods = {process_filename(f, minecraft_version)[0].lower() for f in os.listdir(update_folder) if f.endswith(".jar")}
        
        for name, version in mod_versions.items():
            if name.lower() not in existing_mods:
                f.write(f"{name}: {version}\n")

        f.write(f"\nMods Updated: {mods_updated} New Mods: {mods_new}")

    print(f"Processed filenames saved to {output_file}\n")


def compare_versions(v1, v2):
    """Compares two version strings and returns:
       - 1 if v1 is greater,
       - -1 if v2 is greater,
       - 0 if they are equal.
    """
    v1_parts = [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', v1)]
    v2_parts = [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', v2)]
    
    return (v1_parts > v2_parts) - (v1_parts < v2_parts)

def delete_duplicate_mods(folder, minecraft_version):
    mod_files = {}
    mods_removed = []

    for filename in os.listdir(folder):
        if not filename.endswith(".jar"):  # Ignore non-.jar files
            continue

        name, version = process_filename(filename, minecraft_version)
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
    print("Duplicate mods removed, keeping only the highest versions.\n")

def cleanup_names_given_list(files, minecraft_version):
    newFiles=[]
    for filename in files:
        name, version = process_filename(filename, minecraft_version)
        newFiles.append(f"{name}: {version}")
    return newFiles

def get_differences(folder1, folder2, minecraft_version):
    output_file = os.path.join(folder1, "client_and_serverside_mods.txt")
    clientside_files = [f for f in os.listdir(folder1) if f.endswith(".jar")]
    serverside_files = [f for f in os.listdir(folder2) if f.endswith(".jar")]

    clientside_only = [f for f in clientside_files if f not in serverside_files]
    serverside_only = [f for f in serverside_files if f not in clientside_files]
    with open(output_file, "w") as f:
        f.write("Clientside only files:\n")
        clientside_only = cleanup_names_given_list(clientside_only, minecraft_version)
        f.write("\n".join(clientside_only))
        f.write("\n")
        f.write("\nServerside only files:\n")
        serverside_only = cleanup_names_given_list(serverside_only, minecraft_version)
        f.write("\n".join(serverside_only))
    print(f"Clientside only files: {clientside_only}\n")
    print(f"Serverside only files: {serverside_only}\n")
    print("Client and serverside files saved to file: client_and_serverside_mods.txt in the client folder given\n")

def remove_wrong_versions(folder, minecraft_version):
    mods_cleaned = 0
    major, minor = map(int, minecraft_version.split("."))  # Split into major and minor parts
    previous_minecraft_version = f"{major}.{minor - 1}"  # Decrease minor version
    allowed_minecraft_versions = [
    r"1\.7\.10", r"1\.12\.[1-9]", r"1\.16\.[1-9]",
    r"1\.19\.[1-9]", r"1\.20\.[1-9]", r"1\.21\.[1-9]"
    ]
    allowed_versions_pattern = rf"(?<=\d)(?:mc_?|mc-?|\+)?(?:{'|'.join(allowed_minecraft_versions)})(?=$|[-_.+])|(?:^|[-_+])(?:mc_?|mc-?|\+)?(?:{'|'.join(allowed_minecraft_versions)})(?=$|[-_.+])"
    for filename in os.listdir(folder):
        cleaned = cleanup(filename)
        # Check if the file contains the Minecraft version before modifying it
        if re.sub(rf"(?<=\d)(?:mc_?|mc-?|\+)?(?:{previous_minecraft_version}\.[1-9]-)?(?:{minecraft_version})(?:\.[1-9]+|\.X|x)?(?=$|[-_.+])|(?:^|[-_+])(?:mc_?|mc-?|\+)?(?:{previous_minecraft_version}\.[1-9]-)?(?:{minecraft_version})(?:\.[1-9]+|\.X|x)?(?=$|[-_.+])", "", cleaned, flags=re.IGNORECASE):
            # Remove Minecraft version references
            cleaned = re.sub(rf"(?<=\d)(?:mc_?|mc-?|\+)?(?:{previous_minecraft_version}\.[1-9]-)?(?:{minecraft_version})(?:\.[1-9]+|\.X|x)?(?=$|[-_.+])|(?:^|[-_+])(?:mc_?|mc-?|\+)?(?:{previous_minecraft_version}\.[1-9]-)?(?:{minecraft_version})(?:\.[1-9]+|\.X|x)?(?=$|[-_.+])", "", cleaned, flags=re.IGNORECASE)

        else:
            # If the Minecraft version isn't found and they don't have one delete the file
            #print("cleaned file: " + cleaned + "\n") this was debug
            has_minecraft_version = re.search(allowed_versions_pattern, cleaned, flags=re.IGNORECASE)
            if not has_minecraft_version:
                continue
            file_path = os.path.join(folder, filename)
            os.remove(file_path)  # Delete the file
            mods_cleaned +=1
            print("Deleting %s because it's not the right version" % filename)
    print(f"{mods_cleaned} mods removed.\n")
    return

if __name__ == "__main__":
    check_process = "0"
    check_minecraft = "0"
    print("Welcome to the Minecraft mod manager!")
    while check_minecraft == "0":
        check_minecraft = input(
            "Please select a minecraft version:\n"
            "1. 1.21.X\n"
            "2. 1.20.X\n"
            "3. 1.19.X\n"
            "4. 1.12.X\n"
            "5. 1.7.10\n"
        )
        if check_minecraft not in {"1", "2", "3", "4", "5"}:
            print("Press a number between 1 and 5 please.\n")
            check_minecraft = "0"
        if check_minecraft == "1":
            minecraft_version = "1.21"
        elif check_minecraft == "2":
            minecraft_version = "1.20"
        elif check_minecraft == "3":
            minecraft_version = "1.19"
        elif check_minecraft == "4":
            minecraft_version = "1.12"
        elif check_minecraft == "5":
            minecraft_version = "1.7.10"
    
    while check_process == "0":
        check_process = input(
            "Select an option:\n"
            "1. Check update mods for incorrect minecraft versions.\n"
            "2. Delete duplicate mods in the update folder.\n"
            "3. Compare folders and update the version update file.\n"
            "4. Find clientside and serverside-only files.\n"
            "5. Exit.\n"
        )

        if check_process not in {"1", "2", "3", "4", "5"}:
            print("Press a number between 1 and 5 please.\n")
            check_process = "0"
                
        if check_process == "1":
            folder = input("Enter the folder path: ")
            remove_wrong_versions(folder, minecraft_version)
            check_process = "0"
        elif check_process == "2":
            folder = input("Enter the folder path: ")
            delete_duplicate_mods(folder, minecraft_version)
            check_process = "0"
        elif check_process == "3":
            folder1 = input("Enter the main folder path: ")
            folder2 = input("Enter the updates folder path: ")
            process_folders(folder1, folder2, minecraft_version)
            check_process = "0"
        elif check_process == "4":
            folder1 = input("Enter the client folder path: ")
            folder2 = input("Enter the server folder path: ")
            get_differences(folder1, folder2, minecraft_version)
            check_process = "0"
        elif check_process == "5":
            print("Exiting...")
            break