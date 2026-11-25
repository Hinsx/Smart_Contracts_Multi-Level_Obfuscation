// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EscrowVault {
enum State {
AWAITING_PAYMENT,
AWAITING_DELIVERY,
COMPLETE,
REFUNDED
}

address public immutable buyer;
address public immutable seller;
address public immutable arbiter;

State public state;
uint256 public amount;

event Deposited(address indexed buyer, uint256 amount);
event Released(address indexed seller, uint256 amount);
event Refunded(address indexed buyer, uint256 amount);

constructor(address seller_, address arbiter_) {
require(seller_ != address(0), "Escrow: zero seller");
require(arbiter_ != address(0), "Escrow: zero arbiter");
buyer = msg.sender;
seller = seller_;
arbiter = arbiter_;
state = State.AWAITING_PAYMENT;
}

function deposit() external payable {
require(msg.sender == buyer, "Escrow: only buyer");
require(state == State.AWAITING_PAYMENT, "Escrow: wrong state");
require(msg.value > 0, "Escrow: no value");
amount = msg.value;
state = State.AWAITING_DELIVERY;
emit Deposited(msg.sender, msg.value);
}

function confirmDelivery() external {
require(msg.sender == buyer, "Escrow: only buyer");
require(state == State.AWAITING_DELIVERY, "Escrow: wrong state");
state = State.COMPLETE;
(bool _0xa3b179, ) = payable(seller).call{value: amount}("");
require(_0xa3b179, "Escrow: release failed");
emit Released(seller, amount);
}

function refund() external {
require(msg.sender == arbiter, "Escrow: only arbiter");
require(state == State.AWAITING_DELIVERY, "Escrow: wrong state");
state = State.REFUNDED;
uint256 _0x1c8031 = amount;
amount = 0;
(bool _0x06671a, ) = payable(buyer).call{value: _0x1c8031}("");
require(_0x06671a, "Escrow: refund failed");
emit Refunded(buyer, _0x1c8031);
}
}
