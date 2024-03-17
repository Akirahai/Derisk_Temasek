from loguru import logger
import mysql.connector
import os
import pandas as pd
import datetime

def connect_to_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=os.getenv("MYSQLUSERNAME"), 
            password=os.getenv("MYSQLPASSWORD"), 
            database="proj"
        )
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Database connection failed: {e}")
        return None

def get_all_companies():
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM companies"
            cursor.execute(query)
            
            # Fetch all records
            rows = cursor.fetchall()
            
            # Get column names
            column_names = [i[0] for i in cursor.description]
            
            # Create DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            # Close cursor and connection
            cursor.close()
            conn.close()
        
            return df
        except mysql.connector.Error as e:
            logger.error(f"Failed to get tracking companies: {e}")
    return pd.DataFrame()  # Return empty DataFrame in case of error

def batch_create_companies(company_data):
    print(f"creating entries:{company_data}")
    conn = connect_to_db()
    if conn:
        try:
            c = conn.cursor()
            query = """
            INSERT INTO companies (isin, asset_name, description, country_of_exposure, inst_type, market_cap)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE isin=VALUES(isin)
            """
            c.executemany(query, company_data)
            conn.commit()
        except mysql.connector.Error as e:
            logger.error(f"Failed to batch create companies: {e}")
        finally:
            conn.close()


def batch_insert_asset_prices(asset_price_data):
    conn = connect_to_db()
    if conn:
        try:
            c = conn.cursor()
            # Iterate through each asset price data tuple
            for price_data in asset_price_data:
                isin, date, price = price_data
                # Get the company ID using the ISIN
                c.execute("SELECT id FROM companies WHERE isin = %s", (isin,))
                company_id_result = c.fetchone()

                # If a company ID is found, insert the price data with IGNORE to skip duplicates
                if company_id_result:
                    company_id = company_id_result[0]
                    insert_query = """
                    INSERT IGNORE INTO asset_prices (company_id, date, price)
                    VALUES (%s, %s, %s)
                    """
                    c.execute(insert_query, (company_id, date, price))
                else:
                    logger.warning(f"No company found for ISIN: {isin}")
            conn.commit()
        except mysql.connector.Error as e:
            logger.error(f"Failed to batch insert asset prices: {e}")
        finally:
            conn.close()


def get_price_history(isins, start_date, end_date):
    if not isins:  # Check if the isins list is empty
        return pd.DataFrame()  # Return an empty DataFrame immediately if there are no ISINs
    
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            format_strings = ','.join(['%s'] * len(isins))
            query = f"""
                SELECT c.isin, ap.date, ap.price
                FROM companies c
                JOIN asset_prices ap ON c.id = ap.company_id
                WHERE c.isin IN ({format_strings}) AND ap.date BETWEEN %s AND %s
                ORDER BY c.isin, ap.date
            """
            
            cursor.execute(query, isins + [start_date, end_date])
            
            # Fetch all records
            rows = cursor.fetchall()
            
            # Get column names
            column_names = [i[0] for i in cursor.description]
            
            # Create DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            # Close cursor and connection
            cursor.close()
            conn.close()
            
            return df
        except mysql.connector.Error as e:
            logger.error(f"Failed to get price history: {e}")
            return pd.DataFrame()  # Return empty DataFrame in case of error

def get_extracted_sentiment(isin, start_date, end_date):
    conn = connect_to_db()
    if conn: 
        try:   
            cursor = conn.cursor()
            query = """
                SELECT ms.extractedsentiment, ms.sentiment_type, ss.source_link
                FROM media_sentiments ms
                JOIN companies c ON ms.company_id = c.id
                JOIN sentiments_sources ss ON ms.id = ss.sentimentid
                WHERE c.isin = %s AND ss.timestamp BETWEEN %s AND %s
            """
            
            cursor.execute(query, (isin, start_date, end_date))
            
            # Fetch all records
            rows = cursor.fetchall()
            
            # Get column names
            column_names = [i[0] for i in cursor.description]
            
            # Create DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            # Close cursor and connection
            cursor.close()
            conn.close()
            
            return df
        except mysql.connector.Error as e:
            logger.error(f"Failed to get {isin} sentiment: {e}")
            return pd.DataFrame()  # Return empty DataFrame in case of error

def insert_sentiments_and_sources(company_id, sentiments, sentiment_type):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            conn.start_transaction()
            current_date = datetime.date.today()  # Get current date

            for sentiment in sentiments:
                # print(f'Debugging check: inserting sentiment into db : \n {sentiment}') 
                insert_sentiment_query = """
                    INSERT INTO media_sentiments (company_id, extracted_sentiment, date, sentiment_type) 
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_sentiment_query, (company_id, sentiment['sentiment'], current_date, sentiment_type))
                sentiment_id = cursor.lastrowid

                for source_link in sentiment['sources']:
                    # print(f'Debugging check: inserting soruce into db : \n {source_link} \n for {sentiment}') 
                    insert_source_query = """
                        INSERT INTO sentiment_sources (media_sentiment_id, source_link) 
                        VALUES (%s, %s)
                    """
                    cursor.execute(insert_source_query, (sentiment_id, source_link))

            conn.commit()
        except mysql.connector.Error as e:
            print(f"Error: {e}")
            conn.rollback()
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

def get_company_id_by_isin(isin):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT id FROM companies WHERE isin = %s"
            cursor.execute(query, (isin,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return result[0] if result else None
        except mysql.connector.Error as e:
            logger.error(f"Failed to get company by isin: {e}")
            return None

def get_company_id_by_name(name):
    conn = connect_to_db()
    if conn: 
        try:
            cursor = conn.cursor()
            query = "SELECT id FROM companies WHERE asset_name LIKE %s"
            search_pattern = f"%{name}%"
            cursor.execute(query, (search_pattern,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return result[0] if result else None
        except mysql.connector.Error as e:
            logger.error(f"Failed to get company name: {e}")
            return None

def check_url_in_sentiment_sources(url):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                SELECT COUNT(*) FROM sentiment_sources WHERE source_link = %s
            """
            cursor.execute(query, (url,))
            result = cursor.fetchone()[0]
            return 1 if result > 0 else 0
        except mysql.connector.Error as e:
            print(f"Error: {e}")
            return 0  # Return 0 in case of error
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()


def get_media_sentiments_df(conn, start_date, end_date):
    media_sentiments_query = """
        SELECT ms.id, c.isin, c.asset_name, ms.extracted_sentiment, ms.sentiment_type, ms.date
        FROM media_sentiments ms
        JOIN companies c ON ms.company_id = c.id
        WHERE ms.date BETWEEN %s AND %s
    """
    cursor = conn.cursor()
    cursor.execute(media_sentiments_query, (start_date, end_date))
    rows = cursor.fetchall()
    cursor.close()
    
    # Assuming you know the column names and order
    columns = ['id', 'isin', 'asset_name', 'extracted_sentiment', 'sentiment_type', 'date']
    media_sentiments_df = pd.DataFrame(rows, columns=columns)
    return media_sentiments_df

def get_sentiment_sources_df(conn):
    sentiment_sources_query = """
        SELECT media_sentiment_id, source_link
        FROM sentiment_sources
    """
    cursor = conn.cursor()
    cursor.execute(sentiment_sources_query)
    rows = cursor.fetchall()
    cursor.close()
    
    columns = ['media_sentiment_id', 'source_link']
    sentiment_sources_df = pd.DataFrame(rows, columns=columns)
    return sentiment_sources_df


def merge_sentiments_with_sources(media_sentiments_df, sentiment_sources_df):
    merged_df = pd.merge(media_sentiments_df, sentiment_sources_df, left_on='id', right_on='media_sentiment_id', how='left')
    merged_df['source_links'] = merged_df.groupby('id')['source_link'].transform(lambda x: list(x))
    merged_df = merged_df.drop(['media_sentiment_id', 'source_link'], axis=1).drop_duplicates()
    return merged_df

def reportHelper(start_date,end_date):
    conn = connect_to_db()
    media_sentiments_df = get_media_sentiments_df(conn, start_date, end_date)
    sentiment_sources_df = get_sentiment_sources_df(conn)
    merged_df = merge_sentiments_with_sources(media_sentiments_df, sentiment_sources_df)
    # Close database connection
    conn.close()
    return merged_df

