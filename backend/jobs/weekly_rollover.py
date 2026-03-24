\
\
\
\
\
\
\
\
\
   
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    now = datetime.now()
    iso = now.isocalendar()
    week_num, year = iso[1], iso[0]
    logger.info("Weekly rollover: start of week %d, year %d", week_num, year)

if __name__ == "__main__":
    main()
