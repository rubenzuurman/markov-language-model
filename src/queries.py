create_markov_data_table = """
    CREATE TABLE markov_data (
        prev_tokens VARCHAR(32) NOT NULL,
        next_token VARCHAR(1) NOT NULL,
        frequency INTEGER NOT NULL,
        CONSTRAINT abc UNIQUE (prev_tokens, next_token)
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

select_markov_data_table = """
    SELECT * FROM markov_data;
"""

# Used to test the program.
select_markov_data_table_limit10 = """
    SELECT * FROM markov_data ORDER BY frequency DESC LIMIT 10;
"""

query_next_token = """
    SELECT next_token, frequency FROM markov_data WHERE prev_tokens=?;
"""

insert_combo = """
    INSERT INTO markov_data (prev_tokens, next_token, frequency) 
        VALUES (?, ?, ?) 
        ON CONFLICT (prev_tokens, next_token) 
        DO UPDATE SET frequency=frequency+EXCLUDED.frequency;
"""