# markov-language-model

Markov language model with sqlite3 in python.

The following functions will be created:

- cleanup_wikipedia_data(*src_path*, *dest_path*): Reads response from https://en.wikipedia.org/api/rest_v1/page/html/{title} from the source file, removes all sources and invalid characters, puts every sentence on a new line, and writes the result to the destination file.
- create_new_database(*database_name*): Create a new database and add necessary tables.
- train_database_on_dataset(*database_name*, *dataset_file*): Loop over all sentences in the dataset and add the data to the dataset.
- generate_sentence(*database*, *sentence_start*, *max_length*): Generate a sentence with the specified sentence start. Stop generating at sentence end marker (a dot) or at max length.