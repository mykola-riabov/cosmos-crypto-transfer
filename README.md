# cosmos-crypto-transfer
The application is designed for IBC token transfers between different Cosmos chains.
Popular wallets use a block height timeout, which means that they wait for a transaction to be confirmed by a certain number of blocks before considering it complete. This can take several hours, or even longer in some cases.

If a transaction is not confirmed within the specified time period, popular wallets will usually cancel it and return the funds to the sender. This can be inconvenient if the transaction was sent as an arbitration transaction, as it can delay the resolution of the dispute.

Cosmos-crypto-transfer uses a time-based timeout, which means that it waits for a specified amount of time before considering a transaction complete. This is usually much faster than a block height timeout, making cosmos-crypto-transfer more convenient for arbitration transactions.

![book.png](screen%2Fbook.png)

![price.png](screen%2Fprice.png)

![action.png](screen%2Faction.png)