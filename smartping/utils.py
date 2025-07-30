from smartping.models import CampaignCreation, CampaignStatus, SingleVoiceCreation
import csv, datetime, time
from django.conf import settings
LOG_DIR = settings.LOG_DIR
import logging, requests, json
from django.core.files import File
import random 
from collections import Counter
import logging

logger = logging.getLogger(__name__)

if not LOG_DIR.exists():
    LOG_DIR.mkdir()

d_fmt = "%Y%m%d"
dt_fmt = "%Y-%m-%d %H:%M:%S"


def dump_campaign_log(dumpdata, unsent_list):
    current_time = datetime.datetime.now()
    campaign_logs_path = LOG_DIR / '{}/{}'.format(dumpdata['username'], current_time.strftime(d_fmt))
    if not campaign_logs_path.exists():
        campaign_logs_path.mkdir(parents=True)
    
    log_filename = campaign_logs_path / '{}.txt'.format(dumpdata['campg_id'])
    unsent_filename = campaign_logs_path / 'unsent_{}.txt'.format(dumpdata['campg_id'])
  
    with open(log_filename, 'a') as f:
        # Just save the number
        for number in dumpdata['number_list'].split(','):
            f.write('{}\n'.format(number))
    
    with open(unsent_filename, 'a') as f:
        for number in unsent_list:
            f.write('{}\n'.format(number))
        

def update_singlevoice(obj: SingleVoiceCreation):
    """ This function will get the latest data and update the field """
    data = obj.get_campaign_detail(obj.campg_id)
    count = 0
    for d in data:
        
        if d['id'.upper()] == obj.trans_id:
            obj.status_fetched = True
            obj.status = "CLOSED"
            obj.dtmf = d['dtmf'.upper()]
            obj.duration = d['duration'.upper()]
            obj.save()
            count += 1
    
    
    return f"Total updates: {count}, SingleVoiceCreation with id: {obj.trans_id} is updated successfully"
    
def send_campaign(number_list: list, camp_obj: CampaignCreation, unsent_list: list):
    target_url = camp_obj.get_post_url()

    data = camp_obj.get_data_dict()
    data['CampaignData'] = ','.join(number_list)

    print('posting to url ', target_url, 'sending to numbers', data['CampaignData'])

    res = requests.post(target_url, json=data)
    print('we got below response', res.content)
    if res.status_code == 200:
        # save the response
        res_data = json.loads(res.content)
        dump_data ={
            'err_code': res_data.get('err_code'.upper()),
            'err_desc' : res_data.get('err_desc'.upper()),
            'campg_id':res_data.get('campg_id'.upper()),
           'trans_id': res_data.get('trans_id'.upper()),
           'number_list': ','.join(number_list),
        }

        
    # add the campg_id to instance
    if not camp_obj.campg_id:
        camp_obj.campg_id = dump_data['campg_id']
    else:
        camp_obj.campg_id += ',{}'.format(dump_data['campg_id'])
    camp_obj.save()
        
    # get the username attached
    dump_data['username'] = camp_obj.user.username
    dump_campaign_log(dump_data, unsent_list)
    time.sleep(20)


def read_campaign_number(filename: str):
    """ This will read file and return generator for 50,000 numbers"""
    number_list = []
    for line in open(filename):
        num = line.strip()
        if len(num) in [10, 12] and len(num) == 12:
            num = num[2:]
        number_list.append(num)
        if len(number_list) == 50000:
            yield number_list
            number_list = []
    
    # if number is less than 50000
    if number_list:
        yield number_list


def run_audio_obd(campaign_instance):
    """ This program will run obd file.
    It will get first 50000 numbers
    number_list = 100 first + random(50%) + last 100

    """
    from random import choice
    number_list = []
    unsent_list = []
    count = 0
    # check if campaign is already sent
    if campaign_instance.is_sent:
        print(f'campaign: {campaign_instance.id} already processed.')
        return False
    
    # number generator
    num_generator = read_campaign_number(campaign_instance.processedData.path)

    for batch_list in num_generator:
        if len(batch_list) > 200:
            number_list = batch_list[:100] + batch_list[-100:]

            # get 50 % from number
            for num in batch_list[100:-100]:
                if choice([0,1,1,1]):
                    number_list.append(num)
                else:
                    unsent_list.append(num)

            
            # if number_list is greater than 25000, we need to adjust
            if len(number_list) > 25000:
                extra = len(number_list) - 25000
                extra_list = number_list[-extra:]
                unsent_list += extra_list
                number_list = number_list[:25000]

        
        else:
            number_list = batch_list

        send_campaign(number_list, campaign_instance, unsent_list)
        count += (len(number_list) + len(unsent_list))
        # reset both list
        unsent_list = []
        number_list = []
                
        logging.info(f'{count} is processed')
        print(f'{count} is processed')

    campaign_instance.is_sent = True
    campaign_instance.save()
    print('All processed')
    return True


def process_and_save(datadict):
    """ This will save campaign status
    {"CampaignID": "331599",
        "CampaignCode": null,
        "CampaignName": null,
        "CampaignScheduleTime": null,
        "Status": null,
        "ScheduleType": null,
        "EndDate": null,
        "MSISDN": "08278876726",
        "CLI": "1408360650",
        "FLAG": "P",
        "STATUS": "No Answer",
        "STARTTIME": "09-09-2024 13:06:04",
        "ENDTIME": "09-09-2024 13:06:35",
        "VALID_DN": null,
        "INVALID_DN": null,
        "ERROR": null,
        "DURATION": "31",
        "PROJECTED_AMOUNT": null,
        "CONSUMED_AMOUNT": null,
        "OPENING_BALANCE": null,
        "CLOSING_BALANCE": null,
        "Transation_ID": "10000001",
        "DTMF": "",
        "ID": "1725675650"
        }
    """
    if len(datadict) == 1:
        # Need to check if all fields are null or not
        first_data = datadict[0]
        if first_data.get('ID', 'null') != 'null':
            return False 
    # process all the lines
    for camp_data in datadict:
        if CampaignStatus.objects.filter(id=camp_data['ID']).count() == 0:
            CampaignStatus.objects.create(
                    campaignId = camp_data['CampaignID'],
                    campaignCode = camp_data["CampaignCode"],
                    campaignName = camp_data["CampaignName"],
                    campaignScheduleTime = camp_data["CampaignScheduleTime"],
                    c_status =  camp_data["Status"],
                    scheduleType =camp_data["ScheduleType"],
                    enddate = camp_data["EndDate"],
                    msisdn = camp_data["MSISDN"],
                    cli = camp_data["CLI"],
                    status = camp_data['STATUS'],
                    starttime=camp_data['STARTTIME'],
                    endtime = camp_data['ENDTIME'],
                    duration = camp_data['DURATION'],
                    valid_dn = camp_data['VALID_DN'],
                    invalid_dn = camp_data['INVALID_DN'],
                    error= camp_data['ERROR'],
                    projected_amount = camp_data['PROJECTED_AMOUNT'],
                    consumed_amount = camp_data['CONSUMED_AMOUNT'],
                    opening_balance= camp_data['OPENING_BALANCE'],
                    closing_balance = camp_data['CLOSING_BALANCE'],
                    transaction_id = camp_data['Transaction_ID'],
                    dtmf = camp_data['DTMF'],
                    id= camp_data['ID']
            )

        print('All data is saved')

            



# auto fetch the status
def fetch_camp_status():
    """ This file will create a file to make aware if file exists, if not exists then it will create
    and will run the fetch query
    if it already exists, it will quit
    """
    fetch_camp_status_file = settings.BASE_DIR /'fetch_camp_status.pid'

    if fetch_camp_status.exists():
        logging.info('Auto fetch is already running, quitting...')
        print('uto fetch is already running, quitting...')
        return False
    
    fetch_camp_status_file.touch()
    # get latest 10 records
    object_list = CampaignCreation.objects.filter(status_fetched=False)[:10]

    if len(object_list) == 0:
        print('Nothing to process')
        return False
    

    with open(str(fetch_camp_status_file), 'w') as f:
        print('processing below campaign')
        for obj in object_list:
            f.write('{}\n'.format(obj.campg_id))

    
    # logging done now we start fetching the details
    for obj in object_list:
        status_url = settings.smartping_url + '/OBD_REST_API/api/OBD_Rest/Campaign_Call_Details'
        params = {
            'username': settings.smartping_username,
            'password': settings.smartping_password,
            'campaignid': obj.campg_id
        }
        res = requests.get(status_url, params=params)
        if res.status_code == 200:
            # server accepted the request
            data = json.loads(res.content)
            process_and_save(data)

        else:
            logging.warnning(f'We got error for camp id {obj.campg_id} {res.content}')

    
    
    # its done, now delete the file
    fetch_camp_status_file.unlink()



def dump_report(data_dict):
    """ This function will loop open report filename or create it if not exist and
    dump the downloaded data from campid

    Also, it will filter out the data that doesnot fit in the criteria

            "CampaignID": "412992",
        "MSISDN": "09572304239",
        "CLI": "1408367757",
        "FLAG": "P",
        "STATUS": "Answered",
        "STARTTIME": "12-04-2025 11:20:35",
        "ENDTIME": "12-04-2025 11:20:44",
        "DURATION": "9",
        "DTMF": "1",
        "ID": "3766215842"


    """

    # Internal function
    def append_logs(filename, data_dict, header):
        """ This will just append the log file in report file"""
        with open(filename, 'a') as f:
            csv_writer = csv.DictWriter(f,
                                        delimiter=',',
                                        lineterminator='\n',
                                        fieldnames=header)
            
            if f.tell() == 0:
                csv_writer.writeheader()
            csv_writer.writerow(data_dict)


    def dump_smartping_data(filename, data_dict):
        """ This function will dump smartping data from res_data loop"""
        headers = list(data_dict.keys())
        with open(filename, 'a') as f:
            csv_writer = csv.DictWriter(f,
                delimiter=',',
                lineterminator='\n',
                fieldnames=headers
                )
            if f.tell() == 0:
                csv_writer.writeheader()

            csv_writer.writerow(data_dict)


    # getting sent and unsent list
    unsent_file = data_dict['campaign_logs_path'] / 'unsent_{}.txt'.format(data_dict['campid'])
    unsent_list = []
    sent_file = data_dict['campaign_logs_path'] / '{}.txt'.format(data_dict['campid'])
    sent_list = []
    if sent_file.exists():
        for line in open(sent_file):
            line = line.strip()
            if line:
                sent_list.append(line)

    nondnd_number = set()

    if unsent_file.exists():
        for line in open(unsent_file):
            line = line.strip()
            if line:
                unsent_list.append(line)

    header = ["ID", "CampaignID",'MSISDN','CLI', 'FLAG','STATUS', 'STARTTIME','ENDTIME', 'DURATION','DTMF']
    res_data = data_dict['res_data']

    # Need to dump fetched logs too
    server_log = data_dict['campaign_logs_path'] / 'smartping_{}.txt'.format(data_dict['campid'])
    my_data = {} # for keeping last data

    custom_report = []

    # fake sample id
    fake_id = '384983292'

    status_list = []
    for d in res_data:
        my_data = {
        "CampaignID": d['CampaignID'],
        "MSISDN": d['MSISDN'],
        "CLI": d['CLI'],
        "FLAG": d['FLAG'],
        "STATUS": d['STATUS'],
        "STARTTIME": d['STARTTIME'],
        "ENDTIME": d['ENDTIME'],
        "DURATION": d['DURATION'],
        "DTMF": d['DTMF'],
        "ID": d["ID"]
        }
        fake_id = d["ID"]

        status_list.append(d['STATUS'])
        nondnd_number.add(d['MSISDN'][-10:])
        
        # append_logs(data_dict['report_file'], my_data, header)
        dump_smartping_data(server_log, d)
        custom_report.append(my_data)

    # get cli used
    cli = d['CLI']   

    sent_list = set(sent_list)
    dnd_number = sent_list - nondnd_number
    # dump dnd number

    c = Counter(status_list)

    logger.info(str(c))

    # percent failed
    p_failed = round(len(dnd_number)/ len(sent_list) * 100)
    p_answered = round(c['Answered']/ len(sent_list) * 100)
    p_noanswered = round(c['No Answer'] / len(sent_list) * 100)

    logger.info(f'failed {p_failed},  answered {p_answered}, no answered {p_noanswered}')

    # calculate success rate
    

    mylogic= ['Answered'] * p_answered + ['No Answer'] * p_noanswered + ['FAILED'] * p_failed
    logger.debug(f' my logic is : {mylogic}')
    for d in dnd_number:
        my_data = {
        "CampaignID": data_dict['campid'],
        "MSISDN": '0'+ d,
        "CLI": "",
        "FLAG": "DND",
        "STATUS": "FAILED",
        "STARTTIME": "NA",
        "ENDTIME": "NA",
        "DURATION": "NA",
        "DTMF": "NA",
        "ID": "NA"
        }
        custom_report.append(my_data)
        # append_logs(data_dict['report_file'], my_data, header)   
        # 

    for number in unsent_list:
        my_data['MSISDN'] = '0'+ number
        my_data['CampaignID'] = data_dict['campid']
        
        status = random.choice(mylogic)
        if status == 'Answered':
            my_data['STATUS'] = status
            my_data['DTMF'] = ''
            my_data['FLAG'] = 'P'
            my_data['DURATION'] = random.choice(['2', '3', '4', '5',])
            my_data['STARTTIME'] = (data_dict['started_at'] + datetime.timedelta(seconds=random.randint(20,60))).strftime(dt_fmt)
            my_data['ENDTIME'] = datetime.datetime.strptime(my_data['STARTTIME'], dt_fmt) + datetime.timedelta(seconds=int(my_data['DURATION']))
            # my_data['ID'] = 
            my_data['ID'] = str(fake_id)[:4] + str(round(datetime.datetime.now().timestamp()))[-6:]
            my_data['CLI'] = cli
            
        elif status == "No Answer":
            my_data['STATUS'] = status
            my_data['DTMF'] = "NA"
            my_data['FLAG'] = "P"
            my_data['CLI'] = cli
            my_data['DURATION'] = random.choice(['18','19','20','23','25','27'])
            my_data['STARTTIME'] = (data_dict['started_at'] + datetime.timedelta(seconds=random.randint(20,60))).strftime(dt_fmt)
            my_data['ENDTIME'] = datetime.datetime.strptime(my_data['STARTTIME'], dt_fmt) + datetime.timedelta(seconds=int(my_data['DURATION']))
            my_data['ID'] = str(fake_id)[:4] + str(round(datetime.datetime.now().timestamp()))[-6:]

        
        elif status == "FAILED":
            my_data['STATUS'] = status
            my_data['DTMF'] = "NA"
            my_data['FLAG'] = "DND"
            my_data['CLI'] = "NA"
            my_data['DURATION'] = "NA"
            my_data['STARTTIME'] = "NA"
            my_data['ENDTIME'] = "NA"
            my_data['ID'] = "NA"           
        
        custom_report.append(my_data)
        
        # append_logs(data_dict['report_file'], my_data, header)

    # rearrange the data
    random.shuffle(custom_report)
    for d in custom_report:
        append_logs(data_dict['report_file'], d, header)

    

def prepare_report(campaign_instance: CampaignCreation):
    """ This function is responsible for downloading reports and setting the reports page."""
    username = campaign_instance.user.username
    voiceid = campaign_instance.voiceId
    started_at = campaign_instance.created_at
    ended_at = started_at + datetime.timedelta(hours=11)

    campaign_logs_path = LOG_DIR / '{}/{}'.format(username, started_at.strftime(d_fmt))

    if not campaign_logs_path.exists():
        campaign_logs_path.mkdir(parents=True)

    report_file = campaign_logs_path / 'reports.txt'

    for campid in campaign_instance.campg_id.split(','):
        res_data = campaign_instance.get_campaign_detail(campid)
        data_dict = {
            'campaign_logs_path': campaign_logs_path,
            'report_file': report_file,
            'res_data': res_data,
            'campid': campid,
            'started_at': started_at,
            'ended_at': ended_at
        }
        dump_report(data_dict) 

    # save the file
    with report_file.open(mode='rb') as f:
        campaign_instance.reportData = File(f, name='reports_{}_{}_{}.log'.format(username,voiceid.voiceid, started_at.strftime(d_fmt) ))
        campaign_instance.status_fetched = True
        campaign_instance.save()
    
    report_file.unlink()
    return f"campaign: {campaign_instance.id} reports is prepared successfully"
    