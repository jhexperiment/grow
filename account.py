import csv
import json
from utility import run
from utility import id_generator
from utility import run_retry
from asset import Asset
from random import randint
from wallet import KeyPair
from bootstrapper import BootStrapper


class Account:
    def __init__(self, name, keypair):
        self.name = name
        self.keypair = keypair
        self.amount = Asset(0)

    def __str__(self):
        return json.dumps({'name': self.name, 'pair': str(self.keypair)})

    def toDict(self):
        return { 'account_name': self.name, 'public_key': self.keypair.public, 'private_key': self.keypair.private, 'amount': self.amount }


class AccountFactory:

    def __init__(self, wallet, teclos):
        self.wallet = wallet
        self.teclos = teclos
        self.host_address = 'http://127.0.0.1:8888'

    def set_host_address(self, address):
        self.host_address = address

    def pre_sys_create(self, a):
        #self.wallet.import_key(a.keypair.private)
        run(self.teclos + ' --url %s create account eosio %s %s' % (self.host_address, a.name, a.keypair.public))

    def post_sys_create(self, a, net, cpu, ram, creator='eosio'):
        cmd = self.teclos + ' --url %s system newaccount %s --transfer %s %s --stake-net \"%s\" --stake-cpu \"%s\" --buy-ram \"%s\"'
        net = Asset(net)
        cpu = Asset(cpu)
        ram = Asset(ram)
        run_retry(cmd % (self.host_address, creator, a.name, a.keypair.public, net, cpu, ram))
        a.amount += cpu + net + ram

    #TODO: make sure the account name meetings TELOS normalized requirements
    def get_acc_obj(self, account_name, import_key=False):
        if import_key:
            pair = self.wallet.create_import()
        else:
            pair = self.wallet.create_key()
        a = Account(account_name, pair)
        return a

    def create_random_snapshot(self, num_accounts, min_stake, max_stake, path_to_csv):
        try:
            with open(path_to_csv, 'w', newline='') as csvfile:
                fieldnames = [ 'account_name', 'public_key', 'private_key', 'amount' ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for account in self.create_random_generator(num_accounts, min_stake, max_stake):

                    writer.writerow(account.toDict())
        except Exception as e:
            raise e

    def create_accounts_from_csv(self, path_to_csv):
        try:
            with open(path_to_csv, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                i = 0
                for row in reader:
                    if i == 0:
                        i = i + 1
                        continue
                    amt = float(row['token_amt'])
                    liquid = 0.1000 if amt < 3.0000 else 10.0000 if amt > 11.000 else 2.0000 
                    remainder = amt - liquid
                    cpu = remainder / 2
                    net = remainder - cpu
                    a = Account(row['name'], KeyPair(row['telos_key'], ''))
                    self.post_sys_create(a, net, cpu, 0.03)
        except Exception as e:
            print(e)

    def create_system_accounts(self, account_names):
        accounts = []
        self.wallet.unlock()
        for name in account_names:
            a = self.get_acc_obj(name)
            self.pre_sys_create(a)
            accounts.append(a)
        return accounts

    def create_random_accounts(self, num_accounts, min, max, base="acctname"):
        accounts = []
        min = int(min)
        max = int(max)
        for _ in range(num_accounts):
            a = self.get_acc_obj(base + id_generator(), True)
            cpu = randint(min, max)
            net = randint(min, max)
            ram = randint(min, max)
            self.post_sys_create(a, net, cpu, ram)
            accounts.append(a)
        return accounts

    def create_random_generator(self, num, min, max, base="acctname"):
        min = int(min)
        max = int(max)
        for _ in range(num):
            a = self.get_acc_obj(base + id_generator(), True)
            self.post_sys_create(a, randint(min, max), randint(min, max), randint(min, max))
            toTransfer = Asset(randint(min, max))
            BootStrapper.transfer(self.host_address, 'eosio', a.name, toTransfer, "Initial TLOS Liquid")
            a.amount += toTransfer
            yield a
