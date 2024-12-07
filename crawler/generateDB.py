import psycopg2
from datetime import datetime, timedelta
import random


def create_database(db_config):
    # Connect to default postgres database first
    conn = psycopg2.connect(
        host=db_config.host,
        port=db_config.port,
        database="postgres",  # Connect to default database
        user=db_config.user,
        password=db_config.password
    )
    conn.autocommit = True  # Required for creating database

    try:
        cur = conn.cursor()

        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'crypto_news'")
        exists = cur.fetchone()

        if not exists:
            cur.execute("CREATE DATABASE crypto_news")
            print("Database created successfully")
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        conn.close()


def setup_tables(db_config):
    conn = psycopg2.connect(
        host=db_config.host,
        port=db_config.port,
        database="crypto_news",
        user=db_config.user,
        password=db_config.password
    )

    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cryptocurrencies (
                crypto_id INTEGER PRIMARY KEY,
                symbol VARCHAR(10),
                name VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_mentions (
                id SERIAL PRIMARY KEY,
                crypto_id INTEGER REFERENCES cryptocurrencies(crypto_id),
                fetch_date TIMESTAMP NOT NULL,
                article_id VARCHAR(500) NOT NULL,
                url VARCHAR(255) UNIQUE,
                headline TEXT,
                content TEXT,
                sentiment_score DECIMAL,
                author VARCHAR(500),
                read_count INTEGER,
                published_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS social_mentions (
                id SERIAL PRIMARY KEY,
                crypto_id INTEGER REFERENCES cryptocurrencies(crypto_id),
                fetch_date TIMESTAMP NOT NULL,
                post_id VARCHAR(100) NOT NULL,
                subreddit VARCHAR(50),
                url VARCHAR(255) UNIQUE,
                title TEXT,
                content TEXT,
                score INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                sentiment_score DECIMAL,
                is_post BOOLEAN DEFAULT TRUE,
                author VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS fresh_metrics (
                id SERIAL PRIMARY KEY,
                crypto_id INTEGER REFERENCES cryptocurrencies(crypto_id),
                calculation_time TIMESTAMP NOT NULL,
                time_window INTERVAL NOT NULL,
                news_count INTEGER DEFAULT 0,
                social_count INTEGER DEFAULT 0,
                avg_news_sentiment DECIMAL,
                avg_social_sentiment DECIMAL,
                total_comments INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL
            )
        """)

        # Insert initial data
        cur.execute("TRUNCATE cryptocurrencies CASCADE")

        cur.execute("""
            INSERT INTO cryptocurrencies (crypto_id, symbol, name) VALUES
            (1, 'BTC', 'Bitcoin'),
            (2, 'ETH', 'Ethereum'),
            (3, 'LTC', 'Litecoin')
        """)

        conn.commit()
        print("Tables created and initialized successfully")

    except Exception as e:
        print(f"Error setting up tables: {e}")
        conn.rollback()
    finally:
        conn.close()


def create_sample_data(db_config):
    conn = psycopg2.connect(
        host=db_config.host,
        port=db_config.port,
        database="crypto_news",
        user=db_config.user,
        password=db_config.password
    )

    try:
        cur = conn.cursor()

        # Sample news mentions
        news_data = [
            (crypto_id, datetime.now() - timedelta(hours=random.randint(1, 48)),
             f'article_{i}', f'http://example.com/{i}', f'Headline {i}',
             f'Content {i}', random.uniform(-1, 1), 'Author Name',
             random.randint(100, 1000), datetime.now() - timedelta(hours=random.randint(1, 48)))
            for i in range(100)
            for crypto_id in [1, 2, 3]
        ]

        cur.executemany("""
            INSERT INTO news_mentions 
            (crypto_id, fetch_date, article_id, url, headline, 
             content, sentiment_score, author, read_count, published_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, news_data)

        # Sample social mentions
        social_data = [
            (crypto_id, datetime.now() - timedelta(hours=random.randint(1, 48)),
             f'post_{i}', 'r/bitcoin' if crypto_id == 1 else 'r/ethereum',
             f'http://reddit.com/{i}', f'Title {i}', f'Content {i}',
             random.randint(-100, 1000), random.randint(0, 100),
             random.uniform(-1, 1), True, f'user_{i}')
            for i in range(200)
            for crypto_id in [1, 2, 3]
        ]

        cur.executemany("""
            INSERT INTO social_mentions 
            (crypto_id, fetch_date, post_id, subreddit, url, title,
             content, score, comment_count, sentiment_score, is_post, author)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, social_data)

        conn.commit()
        print("Sample data created successfully")

    except Exception as e:
        print(f"Error creating sample data: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    from dataclasses import dataclass


    @dataclass
    class DBConfig:
        host: str = "localhost"
        port: int = 5432
        database: str = "crypto_news"
        user: str = "postgres"
        password: str = "postgres"


    config = DBConfig()

    # Create database and tables first
    create_database(config)
    setup_tables(config)

    # Then create sample data
    # create_sample_data(config)