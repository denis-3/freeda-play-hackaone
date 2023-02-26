from algosdk import atomic_transaction_composer as a_t_c
from algosdk import v2client, account
from algosdk import transaction as tx

from pyteal import *
from beaker import *

class FreedaPlay(Application):
    adminAccount = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="The admin account. He can configure various settings in the application."
    )

    athleteNftValue = ApplicationStateValue(
        stack_type=TealType.uint64,
        static=True,
        descr="Value of an Athlete NFT in microAlgos",
    )

    isSeasonActive = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="If the football season currently active (0 = inactive, 1 = active)"
    )

    @create
    def create(self):
        return Seq(
            self.initialize_application_state(),
            self.adminAccount.set(Txn.sender()),
            self.isSeasonActive.set(Int(0)),
            self.athleteNftValue.set(Int(1000000)), # 1 Algo
        )

    @opt_in
    def opt_in(self):
        return self.initialize_account_state()

    @external
    def initAthleteNft(self, *, output: abi.Uint64):
        return Seq(
            # Create an Athlete NFT - we can use Jesus as an example
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_name: Bytes("Gabriel Jesus - Freeda Play"),
                TxnField.config_asset_total: Int(1000),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_url: Bytes("https://freeda-play-nft.glitch.me/metadata?id=1"),
                TxnField.config_asset_default_frozen: Int(0),
                TxnField.config_asset_reserve: Global.current_application_address(),
                TxnField.config_asset_manager: Global.current_application_address(),
                TxnField.config_asset_freeze: Global.current_application_address(),
                TxnField.config_asset_clawback: Global.current_application_address(),
            }),
            # Output created Athlete NFT ID
            output.set(InnerTxn.created_asset_id()),
        )

    @external
    def purchaseAthleteNft(self, asset_id: abi.Uint64, *, output: abi.Uint64):
        return Seq(
            # Check that supplied ASA is an Athlete NFT
            creatorCheck := AssetParam.creator(Txn.assets[0]),
            Assert(creatorCheck.hasValue() == Int(1), comment="ASA supplied must exist"),
            Assert(creatorCheck.value() == Global.current_application_address(), comment="ASA supplied must be created by Freeda Play app"),
            # Other basic checks
            Assert(self.isSeasonActive == Int(1), comment="Football season must be active (not currently active)"),
            Assert(Gtxn[0].type_enum() == TxnType.Payment, comment="First Txn in Group must be Payment"),
            Assert(Gtxn[0].receiver() == Global.current_application_address(), comment="Receiver of Payment must be Application"),
            Assert(Gtxn[0].amount() >= self.athleteNftValue, comment="Must transfer at least `athleteNftValue` microAlgos to purchase NFT"),
            # Send the Athlete NFT to Txn.sender()
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.sender: Global.current_application_address(),
                TxnField.asset_receiver: Txn.sender(),
                TxnField.asset_amount: Int(1),
                TxnField.xfer_asset: Txn.assets[0],
            }),
            # Freeze the sent asset if the season is active
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.AssetFreeze,
                TxnField.freeze_asset : Txn.assets[0],
                TxnField.freeze_asset_account: Txn.sender(),
                TxnField.freeze_asset_frozen: self.isSeasonActive.get()
            }),
            # Return the new Athlete NFT balance of Txn.sender()
            balCheck := AssetHolding.balance(Txn.sender(), asset_id.get()),
            output.set(balCheck.value())
        )

    @external
    def sellAthleteNft(self, *, output: abi.Uint64):
        return Seq(
            Assert(self.isSeasonActive == Int(1), comment="Football season must be active (not currently active)"),
            # Has to be a clawback txn since the asset is usually frozen
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_sender: Txn.sender(),
                TxnField.sender: Global.current_application_address(),
                TxnField.asset_receiver: Global.current_application_address(),
                TxnField.asset_amount: Int(1),
                TxnField.xfer_asset: Txn.assets[0]
            }),
            # Reimburse Txn.sender() with proper Algo amount
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.Payment,
                TxnField.amount: self.athleteNftValue,
                TxnField.receiver: Txn.sender()
            }),
            # Return the new Athlete NFT balance of Txn.sender()
            balCheck := AssetHolding.balance(Txn.sender(), Txn.assets[0]),
            output.set(balCheck.value())
        )

    # When the seasons ends, users may want to unfreeze their assets
    @external
    def unlockAsset(self):
        return Seq(
            Assert(self.isSeasonActive == Int(0), comment="Season must not be active"),
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.AssetFreeze,
                TxnField.freeze_asset : Txn.assets[0],
                TxnField.freeze_asset_account: Txn.sender(),
                TxnField.freeze_asset_frozen: Int(0)
            })
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

    @external(read_only = True)
    def getAthleteNftValue(self, *, output: abi.Uint64):
        return output.set(self.athleteNftValue)


def demo(deployedOnPublicNet=False,
        acc_addr=None,
        acc_privkey=None,
        acc_signer=None,
        algod_client=None,
        app_client=None,
        app_addr=None):
    # Setup - if `deployedOnPublicNet` is True, then all other params must be supplied
    acc_addr = sandbox.get_accounts()[0].address if not deployedOnPublicNet else acc_addr
    acc_privkey = sandbox.get_accounts()[0].private_key if not deployedOnPublicNet else acc_privkey
    acc_signer = sandbox.get_accounts()[0].signer if not deployedOnPublicNet else acc_signer
    algod_client = sandbox.get_algod_client() if not deployedOnPublicNet else algod_client

    app_client = client.ApplicationClient(
        client = algod_client,
        app = FreedaPlay(version=8),
        signer = acc_signer,
    ) if not deployedOnPublicNet else app_client

    if not deployedOnPublicNet:
        print("Deploying app...")
        app_id, app_addr, txid = app_client.create()
        print(
            f"""Deployed app in txid {txid}
            App ID: {app_id}
            Address: {app_addr}\n"""
        )

    # Get suggested params before testing
    s_params = algod_client.suggested_params()

    # Begin testing
    print("Funding contract...\n")
    app_client.fund(1000000)

    print("Opting in to the contract...\n")
    app_client.opt_in()

    print("Creating athlete nft...")
    callb = app_client.call(method=FreedaPlay.initAthleteNft)
    asa_id = callb.return_value

    print("The created ASA ID is " + str(asa_id) + "\n")

    print("Opting into created ASA...\n")
    optin_tx = tx.AssetOptInTxn(sender=acc_addr, sp=s_params, index=asa_id)
    algod_client.send_transaction(optin_tx.sign(acc_privkey))

    print("Activating season...")
    calla = app_client.call(method=FreedaPlay.toggleSeason, foreign_assets=[asa_id])
    print("Season status after 1st toggle: " + str(calla.return_value) + "\n")

    print("Checking athlete nft value...")
    call0 = app_client.call(method=FreedaPlay.getAthleteNftValue)
    print("The value of an athlete nft is " + str(call0.return_value / 1000000) + " Algo(s)\n")

    print("Buying athlete nft...")
    pay_tx = tx.PaymentTxn(sender=acc_addr, sp=s_params, receiver=app_addr, amt=1000000 + 2000) # add 2000 for fees
    pay_tx_signer = a_t_c.TransactionWithSigner(txn=pay_tx, signer=acc_signer)
    fundAndCall = a_t_c.AtomicTransactionComposer()
    fundAndCall.add_transaction(pay_tx_signer)
    call = app_client.call(atc=fundAndCall, method=FreedaPlay.purchaseAthleteNft, asset_id=asa_id, foreign_assets=[asa_id])
    print("Athlete NFT balance after buy: " + str(call.return_value) + "\n")

    print("Selling athlete nft...")
    call2 = app_client.call(method=FreedaPlay.sellAthleteNft, foreign_assets=[asa_id])
    print("Athlete NFT balance after sell: " + str(call2.return_value) + "\n")

    print("Deactivating season...")
    call3 = app_client.call(method=FreedaPlay.toggleSeason, foreign_assets=[asa_id])
    print("Season status after 2nd toggle: " + str(call3.return_value) + "\n")

    print("Unlocking asset when season is inactive...\n")
    app_client.call(method=FreedaPlay.unlockAsset, foreign_assets=[asa_id])

    print("Demo finished!")



def deploy(deployOnTestnet, run_demo):
    # Initialize account
    acc_privkey = "your private key here"
    acc_addr = account.address_from_private_key(acc_privkey)
    signer = a_t_c.AccountTransactionSigner(acc_privkey)

    # Initialize client
    algod_token = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    algod_address = 'https://node.testnet.algoexplorerapi.io' # Node URLs provided as sample; any valid node URLs will work
    if not deployOnTestnet:
        input("\nAre you sure you want to deploy Freeda Play application to Algorand MAINNET using account " + acc_addr + "?\nPress ENTER to deploy and control + C to cancel. ")
        algod_address = "https://node.algoexplorerapi.io"

    algod_client = v2client.algod.AlgodClient(algod_token, algod_address)

    app_client = client.ApplicationClient(
        client = algod_client,
        app = FreedaPlay(version=8),
        signer = signer,
    )

    print("\nDeploying app with account " + acc_addr + "...")
    app_id, app_addr, txid = app_client.create()
    print(
        f"""Deployed app in txid {txid}
        App ID: {app_id}
        Address: {app_addr}\n"""
    )

    if run_demo:
        demo(True, acc_addr, acc_privkey, signer, algod_client, app_client, app_addr)



if __name__ == "__main__":
    # Uncomment the following line to deploy app on Algorand Testnet and run demo()
    # deploy(True, True)

    # demo() will deploy the app to the sandbox environment by default
    demo()
