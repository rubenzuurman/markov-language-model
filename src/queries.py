create_users_table = """
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        username VARCHAR(255),
        password VARCHAR(255)
    );
"""

delete_users_table = """
    DROP TABLE users;
"""

insert_user = """
    INSERT INTO users (username, password) VALUES (?, ?);
"""

select_users_table = """
    SELECT * FROM users;
"""

create_markov_data_table = """
    CREATE TABLE markov_data (
        prev_tokens VARCHAR(32),
        next_token VARCHAR(1),
        frequency INTEGER
    );
"""

create_dataset_hashes_table = """
    CREATE TABLE dataset_hashes (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        hash VARCHAR(255)
    );
"""