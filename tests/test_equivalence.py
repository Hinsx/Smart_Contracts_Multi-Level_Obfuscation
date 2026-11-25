"""Functional-equivalence tests for the four benchmark contracts.

Each test deploys a fresh contract on an in-process py-evm chain and covers both the
happy path (state changes + events) and the revert boundaries (unauthorised callers,
bad state, insufficient funds).  When Phase 3/4 start producing obfuscated variants,
the same suite is pointed at them with ``--contract-dir`` and must stay green.
"""

from __future__ import annotations

import pytest

from obf.compiler import compile_source, get_solc_executable, read_source

ZERO_ADDRESS = "0x" + "00" * 20
ETHER = 10**18
SUPPLY = 1_000_000 * ETHER

CONTRACTS = ("Counter", "SimpleERC20", "SimpleAuction", "EscrowVault")


class TestCounter:
    def test_initial_state(self, deploy):
        counter = deploy("Counter", 5)
        assert counter.view("owner") == counter.default_account
        assert counter.view("count") == 5
        assert counter.view("paused") is False

    def test_increment_updates_count_and_emits(self, deploy):
        counter = deploy("Counter", 5)
        receipt = counter.transact("increment")
        assert counter.view("count") == 6
        events = counter.events("CountChanged", receipt)
        assert len(events) == 1
        assert events[0]["args"]["caller"] == counter.default_account
        assert events[0]["args"]["newValue"] == 6

    def test_decrement_reverts_at_zero(self, deploy, expect_revert):
        counter = deploy("Counter", 0)
        expect_revert(
            lambda: counter.contract.functions.decrement().call({"from": counter.default_account}),
            "Counter: underflow",
        )

    def test_reset_is_owner_only(self, deploy, expect_revert):
        counter = deploy("Counter", 9)
        stranger = counter.w3.eth.accounts[1]
        expect_revert(lambda: counter.contract.functions.reset().call({"from": stranger}), "not the owner")
        counter.transact("reset")
        assert counter.view("count") == 0

    def test_set_count_validates_and_updates(self, deploy, expect_revert):
        counter = deploy("Counter", 1)
        counter.transact("setCount", 42)
        assert counter.view("count") == 42
        expect_revert(
            lambda: counter.contract.functions.setCount(42).call({"from": counter.default_account}),
            "value unchanged",
        )

    def test_pause_blocks_mutations(self, deploy, expect_revert):
        counter = deploy("Counter", 2)
        counter.transact("setPaused", True)
        assert counter.view("paused") is True
        expect_revert(
            lambda: counter.contract.functions.increment().call({"from": counter.default_account}),
            "Counter: paused",
        )
        counter.transact("setPaused", False)
        counter.transact("increment")
        assert counter.view("count") == 3

    def test_transfer_ownership_moves_admin_rights(self, deploy, expect_revert):
        counter = deploy("Counter", 3)
        old_owner = counter.default_account
        new_owner = counter.w3.eth.accounts[1]

        counter.transact("transferOwnership", new_owner)
        assert counter.view("owner") == new_owner
        expect_revert(
            lambda: counter.contract.functions.setCount(7).call({"from": old_owner}),
            "not the owner",
        )
        counter.transact("setCount", 7, from_=new_owner)
        assert counter.view("count") == 7
        expect_revert(
            lambda: counter.contract.functions.transferOwnership(ZERO_ADDRESS).call({"from": new_owner}),
            "zero owner",
        )


class TestSimpleERC20:
    def _token(self, deploy, w3, supply: int = SUPPLY):
        accounts = w3.eth.accounts
        return deploy("SimpleERC20", "Demo Token", "DEMO", supply, accounts[9])

    def test_metadata_and_initial_balance(self, deploy, w3):
        token = self._token(deploy, w3)
        assert token.view("name") == "Demo Token"
        assert token.view("symbol") == "DEMO"
        assert token.view("decimals") == 18
        assert token.view("totalSupply") == SUPPLY
        assert token.view("balanceOf", token.default_account) == SUPPLY
        assert token.view("feeRecipient") == w3.eth.accounts[9]

    def test_transfer_charges_one_percent_fee(self, deploy, w3):
        token = self._token(deploy, w3)
        accounts = w3.eth.accounts
        sender, recipient, fee_recipient = token.default_account, accounts[1], accounts[9]

        receipt = token.transact("transfer", recipient, 1000)
        assert token.view("balanceOf", sender) == SUPPLY - 1000
        assert token.view("balanceOf", recipient) == 990
        assert token.view("balanceOf", fee_recipient) == 10

        transfers = token.events("Transfer", receipt)
        assert len(transfers) == 2
        assert token.events("FeeCharged", receipt)[0]["args"]["amount"] == 10

    def test_small_transfer_rounds_fee_to_zero(self, deploy, w3):
        token = self._token(deploy, w3)
        recipient = w3.eth.accounts[1]
        token.transact("transfer", recipient, 50)
        assert token.view("balanceOf", recipient) == 50
        assert token.view("balanceOf", w3.eth.accounts[9]) == 0

    def test_transfer_reverts_on_insufficient_balance(self, deploy, w3, expect_revert):
        token = self._token(deploy, w3)
        expect_revert(
            lambda: token.contract.functions.transfer(w3.eth.accounts[1], SUPPLY + 1).call(
                {"from": token.default_account}
            ),
            "ERC20: insufficient balance",
        )

    def test_transfer_reverts_on_zero_address(self, deploy, w3, expect_revert):
        token = self._token(deploy, w3)
        expect_revert(
            lambda: token.contract.functions.transfer(ZERO_ADDRESS, 1).call({"from": token.default_account}),
            "ERC20: transfer to zero address",
        )

    def test_approve_and_transfer_from_spends_allowance(self, deploy, w3):
        token = self._token(deploy, w3)
        accounts = w3.eth.accounts
        owner, spender, recipient = token.default_account, accounts[1], accounts[2]

        token.transact("approve", spender, 500)
        assert token.view("allowance", owner, spender) == 500

        token.transact("transferFrom", owner, recipient, 200, from_=spender)
        assert token.view("allowance", owner, spender) == 300
        assert token.view("balanceOf", recipient) == 198
        assert token.view("balanceOf", accounts[9]) == 2
        assert token.view("balanceOf", owner) == SUPPLY - 200

    def test_transfer_from_reverts_without_allowance(self, deploy, w3, expect_revert):
        token = self._token(deploy, w3)
        accounts = w3.eth.accounts
        token.transact("approve", accounts[1], 100)
        expect_revert(
            lambda: token.contract.functions.transferFrom(token.default_account, accounts[2], 101).call(
                {"from": accounts[1]}
            ),
            "ERC20: insufficient allowance",
        )

    def test_approve_reverts_on_zero_address(self, deploy, w3, expect_revert):
        token = self._token(deploy, w3)
        expect_revert(
            lambda: token.contract.functions.approve(ZERO_ADDRESS, 1).call({"from": token.default_account}),
            "ERC20: approve to zero address",
        )


class TestSimpleAuction:
    DURATION = 3600

    def _auction(self, deploy, w3):
        beneficiary = w3.eth.accounts[5]
        return deploy("SimpleAuction", beneficiary, self.DURATION), beneficiary

    def test_initial_state(self, deploy, w3):
        auction, beneficiary = self._auction(deploy, w3)
        latest = w3.eth.get_block("latest")["timestamp"]
        assert auction.view("beneficiary") == beneficiary
        assert auction.view("auctionEnd") > latest
        assert auction.view("highestBidder") == ZERO_ADDRESS
        assert auction.view("highestBid") == 0
        assert auction.view("ended") is False

    def test_bid_records_highest_bidder(self, deploy, w3):
        auction, _ = self._auction(deploy, w3)
        bidder = w3.eth.accounts[1]
        receipt = auction.transact("bid", from_=bidder, value=ETHER)
        assert auction.view("highestBidder") == bidder
        assert auction.view("highestBid") == ETHER
        event = auction.events("HighestBidIncreased", receipt)[0]
        assert event["args"]["bidder"] == bidder
        assert event["args"]["amount"] == ETHER

    def test_outbid_refund_is_withdrawable(self, deploy, w3):
        auction, _ = self._auction(deploy, w3)
        accounts = w3.eth.accounts
        first, second = accounts[1], accounts[2]

        auction.transact("bid", from_=first, value=ETHER)
        auction.transact("bid", from_=second, value=2 * ETHER)
        assert auction.view("pendingReturns", first) == ETHER
        assert auction.view("highestBidder") == second

        before = w3.eth.get_balance(first)
        auction.transact("withdraw", from_=first)
        assert auction.view("pendingReturns", first) == 0
        assert w3.eth.get_balance(first) > before

    def test_bid_below_highest_reverts(self, deploy, w3, expect_revert):
        auction, _ = self._auction(deploy, w3)
        accounts = w3.eth.accounts
        auction.transact("bid", from_=accounts[1], value=ETHER)
        expect_revert(
            lambda: auction.contract.functions.bid().call({"from": accounts[2], "value": ETHER // 2}),
            "bid too low",
        )

    def test_bid_after_end_reverts(self, deploy, w3, expect_revert, travel):
        auction, _ = self._auction(deploy, w3)
        travel(self.DURATION + 1)
        expect_revert(
            lambda: auction.contract.functions.bid().call({"from": w3.eth.accounts[1], "value": ETHER}),
            "auction ended",
        )

    def test_end_auction_transfers_to_beneficiary(self, deploy, w3, expect_revert, travel):
        auction, beneficiary = self._auction(deploy, w3)
        bidder = w3.eth.accounts[1]
        auction.transact("bid", from_=bidder, value=2 * ETHER)

        expect_revert(
            lambda: auction.contract.functions.endAuction().call({"from": w3.eth.accounts[0]}),
            "not ended yet",
        )

        travel(self.DURATION)
        before = w3.eth.get_balance(beneficiary)
        auction.transact("endAuction")
        assert auction.view("ended") is True
        assert w3.eth.get_balance(beneficiary) - before == 2 * ETHER

    def test_end_auction_twice_reverts(self, deploy, w3, expect_revert, travel):
        auction, _ = self._auction(deploy, w3)
        auction.transact("bid", from_=w3.eth.accounts[1], value=ETHER)
        travel(self.DURATION)
        auction.transact("endAuction")
        expect_revert(
            lambda: auction.contract.functions.endAuction().call({"from": w3.eth.accounts[0]}),
            "already finalized",
        )


class TestEscrowVault:
    def _escrow(self, deploy, w3):
        accounts = w3.eth.accounts
        buyer, seller, arbiter = accounts[0], accounts[1], accounts[2]
        escrow = deploy("EscrowVault", seller, arbiter, from_=buyer)
        return escrow, buyer, seller, arbiter

    def test_roles_and_initial_state(self, deploy, w3):
        escrow, buyer, seller, arbiter = self._escrow(deploy, w3)
        assert escrow.view("buyer") == buyer
        assert escrow.view("seller") == seller
        assert escrow.view("arbiter") == arbiter
        assert escrow.view("state") == 0  # AWAITING_PAYMENT
        assert escrow.view("amount") == 0

    def test_deposit_by_buyer_moves_to_delivery_state(self, deploy, w3):
        escrow, buyer, _, _ = self._escrow(deploy, w3)
        receipt = escrow.transact("deposit", from_=buyer, value=ETHER)
        assert escrow.view("state") == 1  # AWAITING_DELIVERY
        assert escrow.view("amount") == ETHER
        assert escrow.w3.eth.get_balance(escrow.address) == ETHER
        assert escrow.events("Deposited", receipt)[0]["args"]["amount"] == ETHER

    def test_deposit_by_stranger_reverts(self, deploy, w3, expect_revert):
        escrow, _, seller, _ = self._escrow(deploy, w3)
        expect_revert(
            lambda: escrow.contract.functions.deposit().call({"from": seller, "value": ETHER}),
            "Escrow: only buyer",
        )

    def test_confirm_delivery_releases_funds(self, deploy, w3):
        escrow, buyer, seller, _ = self._escrow(deploy, w3)
        escrow.transact("deposit", from_=buyer, value=ETHER)

        before = w3.eth.get_balance(seller)
        escrow.transact("confirmDelivery", from_=buyer)
        assert escrow.view("state") == 2  # COMPLETE
        assert w3.eth.get_balance(seller) - before == ETHER
        assert w3.eth.get_balance(escrow.address) == 0

    def test_confirm_delivery_by_stranger_reverts(self, deploy, w3, expect_revert):
        escrow, buyer, seller, _ = self._escrow(deploy, w3)
        escrow.transact("deposit", from_=buyer, value=ETHER)
        expect_revert(
            lambda: escrow.contract.functions.confirmDelivery().call({"from": seller}),
            "Escrow: only buyer",
        )

    def test_confirm_before_deposit_reverts(self, deploy, w3, expect_revert):
        escrow, buyer, _, _ = self._escrow(deploy, w3)
        expect_revert(
            lambda: escrow.contract.functions.confirmDelivery().call({"from": buyer}),
            "Escrow: wrong state",
        )

    def test_refund_by_arbiter_returns_funds(self, deploy, w3):
        escrow, buyer, _, arbiter = self._escrow(deploy, w3)
        escrow.transact("deposit", from_=buyer, value=ETHER)

        before = w3.eth.get_balance(buyer)
        escrow.transact("refund", from_=arbiter)
        assert escrow.view("state") == 3  # REFUNDED
        assert escrow.view("amount") == 0
        assert w3.eth.get_balance(buyer) - before == ETHER

    def test_refund_by_buyer_reverts(self, deploy, w3, expect_revert):
        escrow, buyer, _, _ = self._escrow(deploy, w3)
        escrow.transact("deposit", from_=buyer, value=ETHER)
        expect_revert(
            lambda: escrow.contract.functions.refund().call({"from": buyer}),
            "Escrow: only arbiter",
        )

    def test_second_deposit_reverts(self, deploy, w3, expect_revert):
        escrow, buyer, _, _ = self._escrow(deploy, w3)
        escrow.transact("deposit", from_=buyer, value=ETHER)
        expect_revert(
            lambda: escrow.contract.functions.deposit().call({"from": buyer, "value": ETHER}),
            "Escrow: wrong state",
        )


# --------------------------------------------------------------------------- #
# Compiler-level checks: LF handling, optimizer matrix and determinism.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("contract_name", CONTRACTS)
def test_contracts_compile_with_and_without_optimizer(contract_name, contract_dir):
    source, source_bytes = read_source(contract_dir / f"{contract_name}.sol")
    assert source_bytes == source.encode("utf-8")

    for optimize in (False, True):
        result = compile_source(source, optimize=optimize, source_name=f"{contract_name}.sol")
        assert result.ast["nodeType"] == "SourceUnit"
        assert result.deployed_bytecode_size > 0
        assert result.deployed_bytecode_size < 24_576, "EIP-170 runtime size limit"
        assert result.opcode_list[0] == "PUSH1"  # runtime dispatch prologue


@pytest.mark.parametrize("contract_name", CONTRACTS)
def test_crlf_source_compiles_identically_to_lf(contract_name, contract_dir):
    lf_text, _ = read_source(contract_dir / f"{contract_name}.sol")
    crlf_text = lf_text.replace("\n", "\r\n")
    assert "\r" in crlf_text

    lf = compile_source(lf_text, source_name=f"{contract_name}.sol")
    crlf = compile_source(crlf_text, source_name=f"{contract_name}.sol")
    assert crlf.bytecode == lf.bytecode
    assert crlf.deployed_bytecode == lf.deployed_bytecode
    assert crlf.ast == lf.ast


def test_compilation_is_deterministic(contract_dir):
    source, _ = read_source(contract_dir / "SimpleERC20.sol")
    first = compile_source(source, source_name="SimpleERC20.sol")
    second = compile_source(source, source_name="SimpleERC20.sol")
    assert first.bytecode == second.bytecode
    assert first.deployed_bytecode == second.deployed_bytecode
    assert first.opcodes == second.opcodes


def test_solc_executable_is_pinned_and_explicit():
    executable = get_solc_executable()
    assert executable.endswith("solc-v0.8.20"), executable
