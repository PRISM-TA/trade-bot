from app.db.session import create_db_session

from app.models.TradeBotDataFeed import TradeBotDataFeed
from app.models.ClassifierResult import ClassifierResult
from app.models.MarketData import MarketData

from sqlalchemy import select, label
from sqlalchemy.orm import aliased
from dotenv import load_dotenv
import os

class DataFeeder:
    def pullData(self, session, ticker: str, classifier_model: str, feature_set: str)->list[TradeBotDataFeed]:
        with session() as db:
            # Create an alias for the subquery
            classifier_subq = (
                select(
                    ClassifierResult.report_date.label('report_date'),
                    ClassifierResult.ticker.label('ticker'),
                    ClassifierResult.model.label('model'),
                    ClassifierResult.feature_set.label('feature_set'),
                    ClassifierResult.uptrend_prob.label('uptrend_prob'),
                    ClassifierResult.side_prob.label('side_prob'),
                    ClassifierResult.downtrend_prob.label('downtrend_prob'),
                    ClassifierResult.predicted_label.label('predicted_label')
                )
                .where(
                    (ClassifierResult.ticker == ticker) &
                    (ClassifierResult.model == model) &
                    (ClassifierResult.feature_set == feature_set)
                )
                .alias('classifier_subq')
            )

            # Perform the main query with a left join
            query = (
                select( 
                    classifier_subq.c.report_date,
                    classifier_subq.c.ticker,
                    classifier_subq.c.model,
                    classifier_subq.c.feature_set,
                    classifier_subq.c.uptrend_prob,
                    classifier_subq.c.side_prob,
                    classifier_subq.c.downtrend_prob,
                    classifier_subq.c.predicted_label,
                    MarketData.open,
                    MarketData.close
                )
                .select_from(
                    classifier_subq.join(
                        MarketData,
                        (classifier_subq.c.report_date == MarketData.report_date)
                        & (classifier_subq.c.ticker == MarketData.ticker)
                    )
                )
            ).order_by(MarketData.report_date)

            query_result = db.execute(query).all()
            return [TradeBotDataFeed(*result) for result in query_result]

ticker = "CVX"
model = "CNNv0"
feature_set = "processed technical indicators (20 days)"

# Step 1 - Pull one year worth of data from the database
load_dotenv()
session = create_db_session(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)

query_result = DataFeeder().pullData(session, ticker, model, feature_set)
print(repr(query_result))