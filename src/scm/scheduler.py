import logging
from datetime import timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from scm.collectors.service import run_collection
from scm.reports.service import generate_report
from scm.settings import TIMEZONE, utcnow

logger = logging.getLogger(__name__)


def scheduled_reports(factory, kind, day=None):
    day = day or (utcnow().astimezone(TIMEZONE).date() - timedelta(days=1))
    with factory.begin() as session:
        return generate_report(session, kind, 'live', day).id


def run_scheduler(factory):
    scheduler = BlockingScheduler(timezone=TIMEZONE, job_defaults={'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 3600})
    scheduler.add_job(run_collection, 'interval', hours=6, args=[factory], id='collect')
    scheduler.add_job(scheduled_reports, 'cron', hour=8, minute=0, args=[factory, 'daily'], id='daily')
    # Monday: previous day is Sunday, selecting the completed prior week.
    scheduler.add_job(scheduled_reports, 'cron', day_of_week='mon', hour=8, minute=10, args=[factory, 'weekly'], id='weekly')
    logger.info('Scheduler: collection 6h, daily 08:00, weekly Monday 08:10 (%s)', TIMEZONE)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)
