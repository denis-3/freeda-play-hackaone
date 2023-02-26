# Freeda Play
### Submission for Hackaone hackathon
Freeda Play is a web3 platform that revolutionizes the paid fantasy sports experience through the utilization of value-preserving non-fungible tokens to represent athletes. Our goal is to eliminate betting and gambling while still offering rewards to users.

## Features
 - _Value-preserving NFTs_: Algorand Standard Assets (ASAs) which can be bought and sold to the smart contract at the same price
 - _Dynamic NFTs_: Metadata is updated dynamically to reflect the real-life performance (e.g. goals) of athletes
 - _Seasonal time-lock_: ASAs are frozen in users' wallets during an active soccer season. Assets can be unfrozen at the end of the season

## Usage
Make sure to install [sandbox](https://github.com/algorand/sandbox), along with the following Python packages:
 - `pyteal`: `pip3 install pyteal`
 - `beaker`: `pip3 install beaker-pyteal`
 - `algosdk`: `pip3 install algosdk`

Start sandbox (`./sandbox up`) and then `freeda_play.py` (`python3 freeda_play.py`). It will then run a demonstration of the features of the smart contract.

## Live Instances
The smart contract is currently deployed to:
 - Algorand Mainnet: [https://algoexplorer.io/application/1047589638](https://algoexplorer.io/application/1047589638)
 - Algorand Testnet: [https://testnet.algoexplorer.io/application/160833764](https://testnet.algoexplorer.io/application/160833764)
