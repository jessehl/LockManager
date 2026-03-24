import requests
import subprocess
import time
from threading import Thread


PORT = '8000'
BASE_URL = f'http://0.0.0.0:{PORT}'
API_KEY = 'test'
NUMBER_OF_THREADS = 30
NUMBER_OF_LOCKS = 1000
SERVER_NAME = "TestServer"

# Start the server, wait for one second so that it can properly boot.
subprocess.Popen(['/server', PORT, 'h', '0', 'a', API_KEY, 't', str(NUMBER_OF_THREADS), 'n', SERVER_NAME])
time.sleep(1)


def test_no_locks():
    # After booting, there should not be any locks.
    status = requests.get(f"{BASE_URL}/status?auth={API_KEY}").json()
    assert not status['locks'], "no locks should be there"


def test_many_locks():
    work = False
    def worker_thread(number):
        while not work:
            time.sleep(0.001)
        get_lock = requests.get(f"{BASE_URL}/getlock?lockname={number}&auth={API_KEY}&lifetime=1000").json()
        assert get_lock['lockacquired'] == True, 'lock should be free'

    # Fire off many requests.
    threads = [Thread(target = worker_thread, args = (number,)) for number in range(NUMBER_OF_LOCKS)]
    [thread.start() for thread in threads]
    work = True
    [thread.join() for thread in threads]

        
    # Check whether there are now NUMBER_OF_LOCKS locks.
    status = requests.get(f"{BASE_URL}/status?auth={API_KEY}").json()
    locks = status['locks']
    number_of_locks = len(locks)
    assert number_of_locks == NUMBER_OF_LOCKS,  f"there should be {NUMBER_OF_LOCKS} locks, but there are only {number_of_locks}"

    # Check if the time remaining is valid for the 'last' lock.
    remaining = locks[-1]['remaining']
    assert remaining <= 1000.0 and remaining > 950.0, "unexpected time remaining"

    
def test_lock_and_release():
    # Get a new lock.
    lock_name = 'test_lock_and_release'
    get_lock = requests.get(f"{BASE_URL}/getlock?lockname={lock_name}&auth={API_KEY}&lifetime=1000").json()
    session_token = get_lock['sessiontoken']

    # Try to acquire the lock again - which should not be possible.
    for _ in range(3):
        acquire = requests.get(f"{BASE_URL}/getlock?lockname={lock_name}&auth={API_KEY}&timeout=0").json()
        assert acquire['lockacquired'] == False, f"lock {lock_name} should not be free"

    # Release the lock.
    released = requests.delete(f"{BASE_URL}/releaselock?lockname={lock_name}&auth={API_KEY}&token={session_token}").json()
    assert released['lockreleased'] == True, 'lock should have been released'

    # The lock should be available now.
    get_lock = requests.get(f"{BASE_URL}/getlock?lockname={lock_name}&auth={API_KEY}&lifetime=1000").json()
    assert get_lock['lockacquired'] == True, 'lock should be free'


def test_lock_and_expire():
    # Test a new lock with a lifetime of 1.
    lock_name = 'test_lock_and_expire'
    requests.get(f"{BASE_URL}/getlock?lockname={lock_name}&auth={API_KEY}&lifetime=1").json()

    # Try to acquire the lock again - which should not be possible NOW.
    again = requests.get(f"{BASE_URL}/getlock?lockname={lock_name}&auth={API_KEY}&timeout=0").json()
    assert again['lockacquired'] == False, f"lock {lock_name} should not be free"

    # The lock should be available after waiting for 1 second.
    again = requests.get(f"{BASE_URL}/getlock?lockname={lock_name}&auth={API_KEY}&timeout=1").json()
    assert again['lockacquired'] == True, f"lock {lock_name} should now be free/expired"
    

def test_long_expiration():
    # Test whether the server accepts a very long timeout (two weeks).
    lock_name = 'expires_after_two_weeks'
    expiration_in_weeks = 2
    expiration_in_seconds = expiration_in_weeks * 7 * 24 * 60 * 60
    requests.get(f"{BASE_URL}/getlock?lockname={lock_name}&auth={API_KEY}&lifetime={expiration_in_seconds}").json()
    locks = requests.get(f"{BASE_URL}/status?auth={API_KEY}").json()['locks']
    lock = [l for l in locks if l['lockname'] == lock_name][0]
    remaining_seconds = lock['remaining']
    assert remaining_seconds <= expiration_in_seconds and remaining_seconds > (expiration_in_seconds - 1)
   


def test_auth():
    # Check that the status/ endpoint can't be queried without api key.
    r = requests.get(f"{BASE_URL}/status")
    assert r.status_code in [401,400], "server should have responded with appropriate http status code"  
    assert 'locks' not in r.json(), "could perform read action without api key"

    # Check that an invalid api key is rejected.
    r = requests.get(f"{BASE_URL}/status?auth=thisIsNotTheRightApiKey")
    assert r.status_code in [401,400], "server should have responded with appropriate http status code"
    assert 'locks' not in r.json(), "could perform read action with wrong api key"

    # Check that no lock can be acquired without api key.
    lock_name = 'no_api_key'
    r = requests.get(f"{BASE_URL}/getlock?lockname={lock_name}")
    assert r.status_code in [400,401], "server should have responded with appropriate http status code"
    assert r.json().get('lockacquired', False) == False, "a lock has been acquired without api key"
    locks = requests.get(f"{BASE_URL}/status?auth={API_KEY}").json()['locks']
    assert len([l for l in locks if l['lockname'] == lock_name]) == 0, "should not have been able to acquire lock without api key"
    

    
    
    
    
    






