create_markov_data_table = """
    CREATE TABLE markov_data (
        prev_tokens VARCHAR(32),
        next_token VARCHAR(1),
        frequency INTEGER
    );
"""

create_dataset_hashes_table = """
    CREATE TABLE dataset_hashes (
        hash VARCHAR(64)
    );
"""

check_hash = """
    SELECT COUNT(*) FROM dataset_hashes WHERE hash=?;
"""

insert_hash = """
    INSERT INTO dataset_hashes (hash) VALUES (?);
"""

check_token_combo_frequency = """
    SELECT frequency FROM markov_data WHERE prev_tokens=? AND next_token=?;
"""

insert_token_combo_frequency = """
    INSERT INTO markov_data (prev_tokens, next_token, frequency) VALUES (?, ?, ?);
"""

update_token_combo_frequency = """
    UPDATE markov_data SET frequency=? WHERE prev_tokens=? AND next_token=?;
"""

select_markov_data_table = """
    SELECT * FROM markov_data ORDER BY frequency DESC LIMIT 10;
"""

query_next_token = """
    SELECT next_token, frequency FROM markov_data WHERE prev_tokens=?;
"""