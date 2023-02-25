from algosdk import atomic_transaction_composer as a_t_c
from algosdk import v2client
from algosdk import transaction as tx

from pyteal import *
from beaker import *

class Freeda(Application):
    athleteNftBalance = ReservedAccountStateValue(
        stack_type=TealType.uint64,
        max_keys=16,
        descr="Athlete NFT balance",
    )

    athleteNftUrl = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Base URL for Athlete NFT metadata"
    )

    adminAccount = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="The admin account. He can configure various settings in the application."
    )

    athleteNftValue = ApplicationStateValue(
        stack_type=TealType.uint64,
        static=True,
        descr="Value of Athlete NFT.",
    )

    isSeasonActive = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="If the football season currently active"
    )

    @create
    def create(self):
        return Seq(
            self.initialize_application_state(),
            self.adminAccount.set(Txn.sender()),
            self.isSeasonActive.set(Int(0)),
            self.athleteNftValue.set(Int(1000000)),
            InnerTxnBuilder.Execute({ # create the value preserving nft on creation
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.asset_amount: Int(1000),
                TxnField.config_asset_name
            }),
        )

    @opt_in
    def opt_in(self):
        return self.initialize_account_state()

    @external
    def purchaseAthleteNft(self, *, output: abi.Uint64):
        return Seq(
            Assert(self.isSeasonActive == Int(1), comment="Football season must be active (not currently active)"),
            Assert(Gtxn[0].type_enum() == TxnType.Payment, comment="First Txn in Group must be Payment"),
            Assert(Gtxn[0].receiver() == Global.current_application_address(), comment="Receiver of Payment must be application"),
            Assert(Gtxn[0].amount() >= self.athleteNftValue, comment="Must transfer at least `athleteNftValue` microAlgos to purchase NFT"),
            self.athleteNftBalance[Bytes("Test")].set(self.athleteNftBalance[Bytes("Test")].get() + Int(1)),
            output.set(self.athleteNftBalance[Bytes("Test")]),
        )

    @external
    def sellAthleteNft(self, *, output: abi.Uint64):
        return Seq(
            Assert(self.isSeasonActive == Int(1), comment="Football season must be active (not currently active)"),
            Assert(self.athleteNftBalance[Bytes("Test")].get() > Int(0), comment="Must have at least 1 athelete NFT to sell"),
            self.athleteNftBalance[Bytes("Test")].set(self.athleteNftBalance[Bytes("Test")].get() - Int(1)),
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.Payment,
                TxnField.amount: self.athleteNftValue,
                TxnField.receiver: Txn.sender()
            }),
            output.set(self.athleteNftBalance[Bytes("Test")]),
        )

    @external
    def toggleSeason(self, *, output: abi.Uint64):
        return Seq(
            Assert(Txn.sender() == self.adminAccount, comment="Sender must be admin"),
            If(self.isSeasonActive == Int(0))
            .Then(self.isSeasonActive.set(Int(1)))
            .Else(self.isSeasonActive.set(Int(0))),
            output.set(self.isSeasonActive)
        )

    @external
    def setAthleteNftUrl(self, newUrl: abi.String, *, output: abi.String):
        return Seq(
            Assert(Txn.sender() == self.adminAccount, comment="Sender must be admin"),
            self.athleteNftUrl.set(newUrl.get()),
            Approve()
        )

    @external(read_only = True)
    def getAthleteNftValue(self, *, output: abi.Uint64):
        return output.set(self.athleteNftValue)

    @external(read_only = True)
    def getAthleteNftUrl(self, *, output: abi.Uint64):
        return output.set(self.athleteNftUrl)


def demo():
    first_acc = sandbox.get_accounts()[0]
    algod_client = sandbox.get_algod_client()
    app_client = client.ApplicationClient(
        client = algod_client,
        app = Freeda(version=8),
        signer = first_acc.signer,
    )
    print("Deploying app...")
    app_id, app_addr, txid = app_client.create()
    print(
        f"""Deployed app in txid {txid}
        App ID: {app_id}
        Address: {app_addr}\n"""
    )

    # creating payment tx to buy athlete nft
    s_params = algod_client.suggested_params()
    pay_tx = tx.PaymentTxn(sender=first_acc.address, sp=s_params, receiver=app_addr, amt=1000000 + 2000) # add 2000 for fees
    pay_tx_signer = a_t_c.TransactionWithSigner(txn=pay_tx, signer=first_acc.signer)

    # atc
    fundAndCall = a_t_c.AtomicTransactionComposer()
    fundAndCall.add_transaction(pay_tx_signer)

    # begin appl
    print("Funding contract...\n")
    app_client.fund(100000 + 1) # fund with minimum balance
    print("Opting in to the contract...\n")
    app_client.opt_in()
    print("Activating season...")
    calla = app_client.call(method=Freeda.toggleSeason)
    print("Season status after 1st toggle: " + str(calla.return_value) + "\n")
    print("Checking athlete nft value...")
    call0 = app_client.call(method=Freeda.getAthleteNftValue)
    print("The value of an athlete nft is " + str(call0.return_value / 1000000) + " Algo(s)\n")
    print("Buying athlete nft...")
    call = app_client.call(atc=fundAndCall, method=Freeda.purchaseAthleteNft)
    print("Test NFT balance after buy: " + str(call.return_value) + "\n")
    # exec = fundAndCall.execute(client=sandbox.get_algod_client(), wait_rounds=100)
    # print(exec.tx_ids)
    input("press enter to continue (up next: sell athlete nft)") # so we can check if funds were actuall transfered
    print("\nSelling athlete nft...")
    call2 = app_client.call(method=Freeda.sellAthleteNft)
    print("Test nft balance after sell: " + str(call2.return_value) + "\n")
    print("Deactivating season...")
    call3 = app_client.call(method=Freeda.toggleSeason)
    print("Season status after 2nd toggle: " + str(call3.return_value))


if __name__ == "__main__":
    demo()
