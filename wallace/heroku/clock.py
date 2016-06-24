"""A clock process."""

from apscheduler.schedulers.blocking import BlockingScheduler
from wallace import db
import os
import imp
import inspect
from psiturk.models import Participant
from datetime import datetime
from psiturk.psiturk_config import PsiturkConfig
from boto.mturk.connection import MTurkConnection
import requests
import smtplib
from email.mime.text import MIMEText
import json

config = PsiturkConfig()
config.load_config()

# Import the experiment.
try:
    exp = imp.load_source('experiment', "wallace_experiment.py")
    classes = inspect.getmembers(exp, inspect.isclass)
    exps = [c for c in classes
            if (c[1].__bases__[0].__name__ in "Experiment")]
    this_experiment = exps[0][0]
    mod = __import__('wallace_experiment', fromlist=[this_experiment])
    experiment = getattr(mod, this_experiment)

except ImportError:
    print "Error: Could not import experiment."

session = db.session

scheduler = BlockingScheduler()


@scheduler.scheduled_job('interval', minutes=0.5)
def check_db_for_missing_notifications():
    """Check the database for missing notifications."""
    aws_access_key_id = os.environ['aws_access_key_id']
    aws_secret_access_key = os.environ['aws_secret_access_key']
    if config.getboolean('Shell Parameters', 'launch_in_sandbox_mode'):
        conn = MTurkConnection(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            host='mechanicalturk.sandbox.amazonaws.com')
    else:
        conn = MTurkConnection(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key)

    # get all participants with status < 100
    participants = Participant.query.all()
    participants = [p for p in participants if p.status < 100]

    # get current time
    current_time = datetime.now()

    # get experiment duration in seconds
    duration = float(config.get('HIT Configuration', 'duration')) * 60 * 60

    # for each participant, if current_time - start_time > duration + 5 mins
    for p in participants:
        p_time = (current_time - p.beginhit).total_seconds()

        if p_time > (duration + 120):
            print ("participant {} with status {} has been playing for too "
                   "long and no notification has arrived - "
                   "running emergency code".format(p.uniqueid, p.status))

            # get their assignment
            assignment_id = p.assignmentid

            # ask amazon for the status of the assignment
            try:
                assignment = conn.get_assignment(assignment_id)[0]
                status = assignment.AssignmentStatus
            except:
                status = None
            print "assignment status from AWS is {}".format(status)
            hit_id = p.hitid

            # general email settings:
            username = os.getenv('wallace_email_username')
            fromaddr = username + "@gmail.com"
            email_password = os.getenv("wallace_email_key")
            toaddr = config.get('HIT Configuration', 'contact_email_on_error')

            if status in ["Submitted", "Approved", "Rejected"]:
                # if it has been submitted then resend a submitted notification
                args = {
                    'Event.1.EventType': 'AssignmentSubmitted',
                    'Event.1.AssignmentId': assignment_id
                }
                requests.post(
                    "http://" + os.environ['HOST'] + '/notifications',
                    data=args)

                # send the researcher an email to let them know
                msg = MIMEText(
                    "Dearest Friend,\n\nI am writing to let you know that at "
                    "{}, during my regular (and thoroughly enjoyable) "
                    "perousal of the most charming participant data table, I "
                    "happened to notice that assignment "
                    "{} has been taking longer than we were expecting. I "
                    "recall you had suggested {} minutes as an upper limit "
                    "for what was an acceptable length of time for each "
                    "assignement, however this assignment had been underway "
                    "for a shocking {} minutes, a full {} minutes over your "
                    "allowance. I immediately dispatched a "
                    "telegram to our mutual friends at AWS and they were able "
                    "to assure me that although the notification "
                    "had failed to be correctly processed, the assignment had "
                    "in fact been completed. Rather than trouble you, "
                    "I dealt with this myself and I can assure you there is "
                    "no immediate cause for concern. "
                    "Nonetheless, for my own peace of mind, I would appreciate"
                    " you taking the time to look into this matter "
                    "at your earliest convenience.\n\nI remain your faithful "
                    "and obedient servant,\nAlfred R. Wallace\n\n"
                    "P.S. Please do not respond to this message, "
                    "I am busy with other matters.".format(
                        datetime.now(),
                        assignment_id,
                        round(duration/60),
                        round(p_time/60),
                        round((p_time-duration)/60)))
                msg['Subject'] = "A matter of minor concern."

                server = smtplib.SMTP('smtp.gmail.com:587')
                server.starttls()
                server.login(username, email_password)
                server.sendmail(fromaddr, toaddr, msg.as_string())
                server.quit()
            else:
                # if it has not been submitted shut everything down
                # first turn off autorecruit
                host = os.environ['HOST']
                host = host[:-len(".herokuapp.com")]
                args = json.dumps({"auto_recruit": "false"})
                headers = {
                    "Accept": "application/vnd.heroku+json; version=3",
                    "Content-Type": "application/json"
                }
                heroku_email_address = os.getenv('heroku_email_address')
                heroku_password = os.getenv('heroku_password')
                requests.patch(
                    "https://api.heroku.com/apps/{}/config-vars".format(host),
                    data=args,
                    auth=(heroku_email_address, heroku_password),
                    headers=headers)

                # then force expire the hit via boto
                conn.expire_hit(hit_id)

                # send the researcher an email to let them know
                msg = MIMEText(
                    "Dearest Friend,\n\nI am afraid I write to you with most "
                    "grave tidings. At {}, during a routine check of the "
                    "usually most delightful participant data table, "
                    "I happened to notice that assignment {} has been taking "
                    "longer than we were expecting. "
                    "I recall you had suggested {} minutes as an upper limit "
                    "for what was an acceptable length "
                    "of time for each assignment, however this assignment had "
                    "been underway for a shocking {} "
                    "minutes, a full {} minutes over your allowance. I "
                    "immediately dispatched a "
                    "telegram to our mutual friends at AWS and they infact "
                    "informed me that they had already sent "
                    "us a notification which we must have failed to process, "
                    "implying that the assignment had "
                    "not been successfully completed. Of course when the "
                    "seriousness of this scenario dawned on me "
                    "I had to depend on my trusting walking stick for "
                    "support: without the notification "
                    "I didn't know to remove the old assignment's data from "
                    "the tables and AWS will have already sent "
                    "their replacement, meaning that the tables may already "
                    "be in a most unsound state!"
                    "\n\nI am sorry to trouble you with this, however, I do "
                    "not know how to proceed so rather than trying "
                    "to remedy the scenario myself, I have instead "
                    "temporarily ceased operations by expiring the HIT "
                    "with the fellows at AWS and have refrained form posting "
                    "any further invitations myself. Once you "
                    "see fit I would be most appreciative if you could "
                    "attend to this issue with the caution, sensitivity "
                    "and intelligence for which I know you so well."
                    "\n\nI remain your faithful and obedient servant,\n"
                    "Alfred R. Wallace"
                    "\n\nP.S. Please do not respond to this message, "
                    "I am busy with other matters.".format(
                        datetime.now(),
                        assignment_id,
                        round(duration/60),
                        round(p_time/60),
                        round((p_time-duration)/60)))
                msg['Subject'] = "Most troubling news."

                server = smtplib.SMTP('smtp.gmail.com:587')
                server.starttls()
                server.login(username, email_password)
                server.sendmail(fromaddr, toaddr, msg.as_string())
                server.quit()

                # send a notificationmissing notification
                args = {
                    'Event.1.EventType': 'NotificationMissing',
                    'Event.1.AssignmentId': assignment_id
                }
                requests.post(
                    "http://" + os.environ['HOST'] + '/notifications',
                    data=args)

scheduler.start()
