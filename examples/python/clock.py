from apscheduler.schedulers.blocking import BlockingScheduler
from sys import stdout

sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=3)
def timed_job():
    print('This job is run every three minutes.')
    stdout.flush()

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=17)
def scheduled_job():
    print('This job is run every weekday at 5pm.')
    stdout.flush()

print('starting scheduler')
stdout.flush()
sched.start()
