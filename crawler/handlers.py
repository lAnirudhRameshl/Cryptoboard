from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import psycopg2
from nltk.sentiment import SentimentIntensityAnalyzer
from psycopg2.extras import RealDictCursor


@dataclass
class DBConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "crypto_news"
    user: str = "postgres"
    password: str = "Passw0rd!"


class Database:
    def __init__(self, config: DBConfig):
        self.config = config
        self.conn = None
        self.connect()

    def connect(self):
        self.conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password
        )
    
    def rollback(self):
        self.conn.rollback()

    def commit(self):
        self.conn.commit()

    def insert_news_mention(self, data: dict):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO news_mentions (crypto_id, fetch_date, article_id, 
                url, headline, content, sentiment_score, author, published_date)
                VALUES (%(crypto_id)s, %(fetch_date)s, %(article_id)s,
                %(url)s, %(headline)s, %(content)s, %(sentiment_score)s, %(author)s, %(published_date)s)
            """, data)
        self.conn.commit()

    def insert_social_mention(self, data: dict):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO social_mentions (crypto_id, fetch_date, post_id, subreddit,
                url, title, content, score, comment_count, sentiment_score, is_post, author, created_at)
                VALUES (%(crypto_id)s, %(fetch_date)s, %(post_id)s, %(subreddit)s,
                %(url)s, %(title)s, %(content)s, %(score)s, %(comment_count)s, 
                %(sentiment_score)s, %(is_post)s, %(author)s, %(created_at)s)
            """, data)
        self.conn.commit()

    def insert_fresh_metrics(self, data: dict):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fresh_metrics (crypto_id, calculation_time, time_window,
                news_count, social_count, avg_news_sentiment, avg_social_sentiment,
                total_comments, total_score, start_time, end_time)
                VALUES (%(crypto_id)s, %(calculation_time)s, %(time_window)s,
                %(news_count)s, %(social_count)s, %(avg_news_sentiment)s,
                %(avg_social_sentiment)s, %(total_comments)s, %(total_score)s,
                %(start_time)s, %(end_time)s)
            """, data)
        self.conn.commit()


class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> float:
        return self.analyzer.polarity_scores(text)['compound']


class MessageHandler(ABC):
    def __init__(self, db: Database):
        self.sentiment = SentimentAnalyzer()
        self.db = db

    @abstractmethod
    def handle(self, message: dict) -> None:
        pass


class NYTHandler(MessageHandler):
    def handle(self, message: dict) -> None:
        try:
            if 'response' in message and 'docs' in message['response']:
                for article in message['response']['docs']:
                    data = {
                        'crypto_id': message['currency'],
                        'fetch_date': datetime.now(),
                        'article_id': article.get('_id'),
                        'url': article.get('web_url'),
                        'headline': article.get('headline', {}).get('main'),
                        'content': article.get('lead_paragraph'),
                        'sentiment_score': self.sentiment.analyze(article.get('headline', {}).get('main', '')),
                        'author': article.get('byline', {}).get('original'),
                        'published_date': article.get('pub_date')
                    }
                    self.db.insert_news_mention(data)
        except Exception as e:
            print(f"Error processing NYT article: {e}")
            self.db.rollback()

    # def _detect_crypto(self, article):
        # # Simple detection - would need to be more sophisticated in production
        # return 1  # Default to Bitcoin for example


class GuardianHandler(MessageHandler):
    def handle(self, message: dict) -> None:
        try:
            if 'response' in message and 'results' in message['response']:
                for article in message['response']['results']:
                    data = {
                        'crypto_id': message['currency'],
                        'fetch_date': datetime.now(),
                        'article_id': article.get('id'),
                        'url': article.get('webUrl'),
                        'headline': article.get('webTitle'),
                        'content': article.get('fields', {}).get('bodyText'),
                        'sentiment_score': self.sentiment.analyze(article.get('webTitle', '')),
                        'author': article.get('fields', {}).get('byline'),
                        'published_date': article.get('webPublicationDate')
                    }
                    self.db.insert_news_mention(data)
        except Exception as e:
            print(f"Error processing Guardian article: {e}")
            self.db.rollback()

    # def _detect_crypto(self, article):
    #     return 1  # Default to Bitcoin for example

class RedditHandler(MessageHandler):
    def handle(self, message):
        try:
            if 'data' in message and 'children' in message['data']:
                for article in message['data']['children']:
                    fetched_data = article.get('data')
                    created_date = datetime.fromtimestamp(fetched_data.get('created_utc'))
                    data = {
                        'crypto_id': message['currency'],
                        'fetch_date': datetime.now(),
                        'post_id': fetched_data.get('id'),
                        'subreddit': fetched_data.get('subreddit_name_prefixed'),
                        'url': "https://reddit.com" + fetched_data.get('permalink'),
                        'title': fetched_data.get('title'),
                        'content': fetched_data.get('selftext'),
                        'score': fetched_data.get('score'),
                        'comment_count': fetched_data.get('num_comments'),
                        'sentiment_score': self.sentiment.analyze(fetched_data.get('title') + '. ' + fetched_data.get('selftext')),
                        'is_post': True,
                        'author': fetched_data.get('author'),
                        'created_at': created_date.isoformat()
                    }
                    self.db.insert_social_mention(data)
        except Exception as e:
            print(f"Error processing Reddit article: {e}")
            self.db.rollback()

class MetricsCalculator:
    def __init__(self, db: Database):
        self.db = db

    def calculate_metrics(self, window_hours: int = 24):
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=window_hours)

            with self.db.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    WITH metrics AS (
                        SELECT 
                            c.crypto_id,
                            COUNT(DISTINCT nm.id) as news_count,
                            COUNT(DISTINCT sm.id) as social_count,
                            AVG(nm.sentiment_score) as avg_news_sentiment,
                            AVG(sm.sentiment_score) as avg_social_sentiment,
                            SUM(sm.comment_count) as total_comments,
                            SUM(sm.score) as total_score
                        FROM cryptocurrencies c
                        LEFT JOIN news_mentions nm ON c.crypto_id = nm.crypto_id 
                            AND nm.fetch_date BETWEEN %s AND %s
                        LEFT JOIN social_mentions sm ON c.crypto_id = sm.crypto_id
                            AND sm.fetch_date BETWEEN %s AND %s
                        GROUP BY c.crypto_id
                    )
                    SELECT * FROM metrics
                """, (start_time, end_time, start_time, end_time))

                results = cur.fetchall()

                for result in results:
                    metrics_data = {
                        **result,
                        'calculation_time': datetime.now(),
                        'time_window': f"{window_hours} hours",
                        'start_time': start_time,
                        'end_time': end_time
                    }
                    self.db.insert_fresh_metrics(metrics_data)

        except Exception as e:
            print(f"Error calculating metrics: {e}")
            self.db.rollback()


class HandlerFactory:
    def __init__(self, db: Database):
        self._handlers = {
            "NYTimes": NYTHandler(db),
            "TheGuardian": GuardianHandler(db),
            "Reddit": RedditHandler(db)
        }

    def get_handler(self, source: str) -> Optional[MessageHandler]:
        return self._handlers.get(source)


db = Database(DBConfig())
factory = HandlerFactory(db)
calculator = MetricsCalculator(db)

# Example usage
# nyt_handler = factory.get_handler("NYTimes")
# if nyt_handler:
#     nyt_handler.handle({"response": {"docs": []}})

# Calculate metrics every X hours
# calculator.calculate_metrics(24)