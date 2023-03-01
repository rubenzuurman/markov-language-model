import re

from bs4 import BeautifulSoup

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

def main():   
    cleanup_wikipedia_data("res/wikipedia_cat.txt", "res/wikipedia_cat_clean.txt")
    cleanup_wikipedia_data("res/wikipedia_dog.txt", "res/wikipedia_dog_clean.txt")

if __name__ == "__main__":
    main()