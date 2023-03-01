import hashlib
import os
import random as rnd
import re
import sqlite3
import sys

from bs4 import BeautifulSoup

import queries

def cleanup_wikipedia_data(src_path, dest_path):
    # Read data from source file.
    try:
        with open(src_path, "rb") as file:
            content = file.read()
    except Exception as e:
        print(f"An error occured while trying to read the source file: {e}")
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
        print(f"An error occured while trying to connect to the database: {e}")
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

def train_database_on_dataset(database_name, dataset_path, markov_chain_length):
    # Get res/ directory.
    res_folder = os.path.join(os.getcwd(), "res")
    
    # Get database path.
    db_path = os.path.join(res_folder, f"{database_name}.dat")
    
    # Create connection.
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"An error occured while trying to connect to the database: {e}")
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
        print(f"An error occured: {e}")
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
    
    # Loop over all lines in the dataset.
    for index, line in enumerate(str(dataset_content).split("\n")):
        # Print message showing the progress so far.
        print(f"Importing line {index}...\r", end="")
        sys.stdout.flush()
        
        # Collect to be added/updated entries in a list.
        to_add = []
        to_update = []
        
        # Loop over all character indices in the line.
        for char_index in range(len(line)):
            # Skip the first few entries where there are less characters 
            # available for prev_tokens than the markov chain length.
            if char_index < markov_chain_length:
                continue
            
            # Get prev_tokens and next_token from line.
            prev_tokens = line[char_index - markov_chain_length:char_index]
            next_token = line[char_index]
            
            # Check if this combination of prev_tokens and next_token already 
            # exists.
            result = c.execute(queries.check_token_combo_frequency, \
                (prev_tokens, next_token))
            
            # Insert the combo if it does not exist, increment if it does.
            result_freq = result.fetchone()
            if result_freq is None:
                # Check if this entry has already been added to the list.
                match_found = False
                for i, (p, n, f) in enumerate(to_add):
                    # Increment the frequency if it already exists.
                    if p == prev_tokens and n == next_token:
                        to_add[i] = (p, n, f + 1)
                        match_found = True
                        break
                # If no match was found, add a new entry.
                if not match_found:
                    to_add.append((prev_tokens, next_token, 1))
            else:
                # Check if this entry has already been added to the list.
                match_found = False
                for i, (f, p, n) in enumerate(to_update):
                    # Increment the frequency if it already exists.
                    if p == prev_tokens and n == next_token:
                        to_update[i] = (f + 1, p, n)
                        match_found = True
                        break
                # If no match was found, add a new entry.
                if not match_found:
                    to_update.append((result_freq[0] + 1, prev_tokens, next_token))
        
        # Execute add and update queries for the whole lists at once.
        c.executemany(queries.insert_token_combo_frequency, to_add)
        c.executemany(queries.update_token_combo_frequency, to_update)
    
    # Print done message.
    print("\nDone!")
    
    # Commit changes.
    conn.commit()
    
    # Close connection.
    conn.close()

def generate_sentence(database_name, sentence_start, max_length, markov_chain_length):
    # Check if the sentence start is at least as long as the markov chain.
    if len(sentence_start) < markov_chain_length:
        print("Sentence start is too short.")
        return
    
    # Get res/ directory.
    res_folder = os.path.join(os.getcwd(), "res")
    
    # Get database path.
    db_path = os.path.join(res_folder, f"{database_name}.dat")
    
    # Create connection.
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"An error occured while trying to connect to the database: {e}")
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

def main():
    # Clean up wikipedia articles about cats and dogs.
    cleanup_wikipedia_data("res/wikipedia_cat.txt", "res/wikipedia_cat_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_dog.txt", "res/wikipedia_dog_clean.txt")
    
    # Create new database, skips if the database already exists.
    create_new_database("banana")
    
    # Train database on datasets, skips if the database is already trained on 
    # these datasets.
    train_database_on_dataset("banana", "res/wikipedia_cat_clean.txt", 5)
    train_database_on_dataset("banana", "res/wikipedia_dog_clean.txt", 5)
    
    # Print 5 random sentences.
    for index, string in enumerate(["The d", "The c", "felin", "dogs ", "histo"]):
        sentence = generate_sentence("banana", string, 250, 5)
        print(index, sentence)

if __name__ == "__main__":
    main()