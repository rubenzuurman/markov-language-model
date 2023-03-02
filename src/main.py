import hashlib
import os
import random as rnd
import re
import requests
import sqlite3
import string
import sys

from bs4 import BeautifulSoup

import queries

def cleanup_wikipedia_data(src_path, dest_path, force_overwrite=False):
    """
    Reads the raw wikipedia page content from the source file, cleans it up, 
    and writes the result to the destination file. If force overwrite is 
    enabled the procedure will be done regardless if the destination file 
    already exists or not.
    """
    # Check types.
    assert isinstance(src_path, str), "Source path must be a string."
    assert isinstance(dest_path, str), "Destination path must be a string."
    
    # Check if the destination file already exists.
    if os.path.isfile(dest_path):
        if not force_overwrite:
            print(f"Destination file already exists '{dest_path}', cleanup " \
                "has been skipped.")
            return
    
    # Read data from source file.
    try:
        with open(src_path, "rb") as file:
            content = file.read()
    except Exception as e:
        print(f"An error occured while trying to read the source file: '{e}'")
        return
    
    # Create soup object and find a paragraph tags.
    soup = BeautifulSoup(content, features="html.parser")
    p = soup.find_all("p")
    
    # Open destination file.
    file = open(dest_path, "wb")
    
    # Loop over all paragraphs.
    for par in p:
        # Get paragraph text.
        text = par.get_text()
        
        # Replace ': .+  ' pattern with space.
        text = re.sub("\[\d*\]: .+ ", "", text)
        
        # Replace ' ' with space.
        text = re.sub(" ", " ", text)
        
        # Replace '[\d*]'' pattern with nothing.
        text = re.sub("\[\d*\]", "", text)
        
        # Replace '[citation needed]' pattern with nothing.
        text = re.sub("\[update\]|\[citation needed\]" \
            "|\[user\-generated source\?\]", "", text)
        
        # Replace ". " with end of sentence token ".\n" to give every 
        # sentence its own line.
        text = re.sub("\. ", ".\n", text)
        
        # Skip empty lines.
        if text.strip() == "":
            continue
        
        # Save result to file.
        file.write(bytes(text + "\n", "utf8"))
    
    # Close destination file.
    file.close()

def create_new_database(database_name):
    """
    Creates a new database in the res/ folder with the extension .dat. The 
    database will contain two tables: 'markov_data' and 'dataset_hashes'.
    """
    # Check types.
    assert isinstance(database_name, str), "Database name must be a string."
    
    # Get res/ directory.
    res_folder = os.path.join(os.getcwd(), "res")
    
    # Create res/ folder if it does not yet exist.
    if not os.path.isdir(res_folder):
        os.mkdir(res_folder)
    
    # Get file path.
    db_path = os.path.join(res_folder, f"{database_name}.dat")
    
    # Check if the database already exists.
    if os.path.isfile(db_path):
        print(f"Database at location '{db_path}' already exists.")
        return
    
    # Create connection.
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"An error occured while trying to connect to the database: '{e}'")
        return
    
    # Create database cursor.
    c = conn.cursor()
    
    # Create markov_data table and dataset_hashes table.
    c.execute(queries.create_markov_data_table)
    c.execute(queries.create_dataset_hashes_table)
    
    # Commit changes.
    conn.commit()
    
    # Close connection.
    conn.close()

def handle_line(line, markov_chain_length):
    # Combos list will store all combos for this line.
    combos = []
    
    # Skip lines that contain non-printable characters.
    if False in [x in string.printable for x in line]:
        return combos
    
    # Loop over all character indices in the line.
    for char_index in range(len(line)):
        # Skip the first few entries where there are less characters 
        # available for prev_tokens than the markov chain length.
        if char_index < markov_chain_length:
            continue
        
        # Get prev_tokens and next_token from line.
        prev_tokens = line[char_index - markov_chain_length:char_index]
        next_token = line[char_index]
        
        # Add new combo to list if it does not exist, else update the entry 
        # in the list with the new frequency.
        match_found = False
        for i, (p, n, f) in enumerate(combos):
            if p == prev_tokens and n == next_token:
                combos[i] = (p, n, f + 1)
                match_found = True
                break
        if not match_found:
            combos.append((prev_tokens, next_token, 1))
    
    # Return combos for this line.
    return combos

def train_database_on_dataset(database_name, dataset_path, markov_chain_length):
    # Check types.
    assert isinstance(database_name, str), "Database name must be a string."
    assert isinstance(dataset_path, str), "Dataset path must be a string."
    assert isinstance(markov_chain_length, int), "Markov chain length must " \
        "be a positive integer."
    assert markov_chain_length > 0, "Markov chain length must " \
        "be a positive integer."
    
    # Get database path.
    db_path = os.path.join(os.getcwd(), "res", f"{database_name}.dat")
    
    # Create connection.
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"An error occured while trying to connect to the database: '{e}'")
        return
    
    # Get dataset path.
    dataset_path = os.path.join(os.getcwd(), dataset_path)
    
    # Hash dataset contents.
    try:
        # Read file and hash contents.
        file = open(dataset_path, "r", encoding="utf-8")
        dataset_content = file.read()
        dataset_hash = hashlib.sha256(dataset_content.encode("utf-8")).hexdigest()
        file.close()
    except Exception as e:
        print(f"An error occured: '{e}'")
        return
    
    # Create database cursor.
    c = conn.cursor()
    
    # Check if this hash is already present in the database.
    result = c.execute(queries.check_hash, (dataset_hash,))
    num_results = result.fetchone()[0]
    if num_results >= 1:
        print(f"Database has already been trained on dataset '{dataset_path}'.")
        return
    
    # Insert hash into database.
    c.execute(queries.insert_hash, (dataset_hash,))
    
    # Initialize master list. This list will contain all markov combo data 
    # for this file.
    master_list = []
    
    # Loop over all lines in the dataset.
    for index, line in enumerate(str(dataset_content).split("\n")):
        # Print message showing the progress so far.
        print(f"Importing line {index} ({len(master_list)} entries so far)...\r", end="")
        sys.stdout.flush()
        
        # Get (prev_tokens, next_token, frequency) combos from line and add 
        # them to the master list.
        combos = handle_line(line, markov_chain_length)
        master_list.extend(combos)
        
    # Execute query for the whole master list at once.
    print("\nExecuting queries...")
    c.executemany(queries.insert_combo, master_list)
    
    # Print done message.
    print("Done!")
    
    # Commit changes.
    conn.commit()
    
    # Close connection.
    conn.close()

def generate_sentence(database_name, sentence_start, max_length, \
    markov_chain_length):
    # Check types.
    assert isinstance(database_name, str), "Database name must be a string."
    assert isinstance(sentence_start, str), "Sentence start must be a string."
    assert len(sentence_start) >= markov_chain_length, "Sentence start " \
        "must have a length equal to or greater than the markov chain length."
    assert isinstance(max_length, int), "Max length must be a positive integer."
    assert max_length > 0, "Max length must be a positive integer."
    assert isinstance(markov_chain_length, int), "Markov chain length must " \
        "be a positive integer."
    assert markov_chain_length > 0, "Markov chain length must " \
        "be a positive integer."
    
    # Check if the sentence start is at least as long as the markov chain.
    if len(sentence_start) < markov_chain_length:
        print("Sentence start is too short.")
        return
    
    # Get database path.
    db_path = os.path.join(os.getcwd(), "res", f"{database_name}.dat")
    
    # Create connection.
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"An error occured while trying to connect to the database: '{e}'")
        return
    
    # Create database cursor.
    c = conn.cursor()
    
    # Set sentence.
    sentence = sentence_start
    
    # Extend sentence with new characters from the database.
    while not sentence.endswith(".") and len(sentence) < max_length:
        # Get prev_tokens from sentence.
        prev_tokens = sentence[-markov_chain_length:]
        
        # Get possible next tokens from database. Return sentence if none are 
        # available.
        result = c.execute(queries.query_next_token, (prev_tokens,))
        options = result.fetchall()
        if options is None:
            return sentence
        
        # Calculate total frequency of all options. If no options exist, 
        # return the sentence.
        total_freq = sum([option[1] for option in options])
        if total_freq == 0:
            return sentence
        
        # Pick a number, whichever option has this number in its frequency 
        # range accumulate start to accumulate end is the winner.
        winner = rnd.randint(0, total_freq - 1)
        freq_accumulate = 0
        next_token = ""
        for token, frequency in options:
            freq_accumulate += frequency
            if winner < freq_accumulate:
                next_token = token
                break
        
        # Append the next token to the sentence.
        sentence += next_token
    
    # Close connection.
    conn.close()
    
    # Return the sentence.
    return sentence

def test_program():
    # Clean up wikipedia articles about cats and dogs.
    cleanup_wikipedia_data("res/wikipedia_cat.txt", "res/wikipedia_cat_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_dog.txt", "res/wikipedia_dog_clean.txt")
    
    # Set database name.
    db_name = "test_db"
    
    # Get database path.
    db_path = os.path.join(os.getcwd(), "res", f"{db_name}.dat")
    
    # Create new database.
    create_new_database(db_name)
    
    # Train database on cat dataset.
    train_database_on_dataset(db_name, "res/wikipedia_cat_clean.txt", 5)
    
    # Open connection and create cursor.
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"TEST: An error occured while trying to connect to the database: '{e}'")
        return
    c = conn.cursor()
    
    # Test if top 10 result is still the same after training on cats.
    expected_result = [(' cats', ' ', 124), (' with', ' ', 69), \
        (' of t', 'h', 68), ('of th', 'e', 63), (' that', ' ', 63), \
        ('omest', 'i', 62), ('mesti', 'c', 62), ('n the', ' ', 62), \
        ('s are', ' ', 59), (' thei', 'r', 58)]
    test_result = c.execute(queries.select_markov_data_table_limit10)
    assert expected_result == test_result.fetchall(), "TEST FAILED: " \
        "Incorrect result after training on cats."
    
    # Close connection.
    conn.close()
    
    # Train database on dog dataset.
    train_database_on_dataset(db_name, "res/wikipedia_dog_clean.txt", 5)
    
    # Open connection and create cursor.
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"TEST: An error occured while trying to connect to the database: '{e}'")
        return
    c = conn.cursor()
    
    # Test if top 10 result is still the same after training on cats and dogs.
    expected_result = [(' with', ' ', 133), (' cats', ' ', 130), \
        (' that', ' ', 123), (' of t', 'h', 120), (' dogs', ' ', 120), \
        ('s and', ' ', 113), ('of th', 'e', 112), ('n the', ' ', 106), \
        (' have', ' ', 103), ('f the', ' ', 98)]
    test_result = c.execute(queries.select_markov_data_table_limit10)
    assert expected_result == test_result.fetchall(), "TEST FAILED: " \
        "Incorrect result after training on cats and dogs."
    
    # Close connection.
    conn.close()
    
    # Delete test database.
    os.remove(db_path)
    
    # Print success message if all tests passed.
    print("TEST SUCCESS!")

def get_wikipedia_page(page_title):
    # Check types.
    assert isinstance(page_title, str), "Page title must be a string."
    
    # Replace spaces with underscores.
    if " " in page_title:
        page_title = page_title.replace(" ", "_")
        print("Warning: Page title cannot contain spaces. Spaces have " \
            "been replaced by underscores, the used page title is " \
            f"'{page_title}'")
    
    # Check if the page has already been requested and saved.
    filename = f"wikipedia_{page_title.lower()}.txt"
    path = os.path.join(os.getcwd(), "res", filename)
    if os.path.isfile(path):
        print(f"Wikipedia page with title '{page_title}' has already been saved.")
        return
    
    # Get page using api.
    url = f"https://en.wikipedia.org/api/rest_v1/page/html/{page_title}"
    response = requests.get(url)
    
    # Check response code.
    if not response.ok:
        print("An error occured while getting the page contents.")
        print(f"Status code {response.status_code}: {response.reason}")
        return
    
    # Write response content to file.
    with open(path, "wb") as file:
        file.write(response.content)
    
    # Print success message.
    print(f"Wikipedia page with title '{page_title}'' has been saved to " \
        f"'{path}'.")

def main():
    # Set database name and markov chain length.
    db_name = "banana"
    markov_chain_length = 8
    
    # Clean up wikipedia articles about cats and dogs.
    cleanup_wikipedia_data("res/wikipedia_cat.txt", "res/wikipedia_cat_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_dog.txt", "res/wikipedia_dog_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_fish.txt", "res/wikipedia_fish_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_mammal.txt", "res/wikipedia_mammal_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_reptile.txt", "res/wikipedia_reptile_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_dinosaur.txt", "res/wikipedia_dinosaur_clean.txt")
    
    # Create new database, skips if the database already exists.
    create_new_database(db_name)
    
    # Train database on datasets, skips if the database is already trained on 
    # these datasets.
    train_database_on_dataset(db_name, "res/wikipedia_cat_clean.txt", markov_chain_length)
    train_database_on_dataset(db_name, "res/wikipedia_dog_clean.txt", markov_chain_length)
    train_database_on_dataset(db_name, "res/wikipedia_fish_clean.txt", markov_chain_length)
    train_database_on_dataset(db_name, "res/wikipedia_mammal_clean.txt", markov_chain_length)
    train_database_on_dataset(db_name, "res/wikipedia_reptile_clean.txt", markov_chain_length)
    train_database_on_dataset(db_name, "res/wikipedia_dinosaur_clean.txt", markov_chain_length)
    
    # Print 5 random sentences.
    for index, string in enumerate(["The dogs", "cats wer", "the morn", "Dinosaur", "History "]):
        sentence = generate_sentence(db_name, string, 250, markov_chain_length)
        print(index, sentence)

if __name__ == "__main__":
    main()
