// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleAuction {
address payable public beneficiary;
uint256 public auctionEnd;
address public highestBidder;
uint256 public highestBid;
bool public ended;

mapping(address => uint256) public pendingReturns;

event HighestBidIncreased(address indexed bidder, uint256 amount);
event AuctionEnded(address indexed winner, uint256 amount);
event Withdrawal(address indexed bidder, uint256 amount);

constructor(address payable beneficiary_, uint256 duration) {
require(beneficiary_ != address(0), "Auction: zero beneficiary");
require(duration > 0, "Auction: zero duration");
beneficiary = beneficiary_;
auctionEnd = block.timestamp + duration;
}

function bid() external payable {
require(!ended, "Auction: already ended");
require(block.timestamp < auctionEnd, "Auction: auction ended");
require(msg.value > highestBid, "Auction: bid too low");

if (highestBid != 0) {
pendingReturns[highestBidder] += highestBid;
}
highestBidder = msg.sender;
highestBid = msg.value;
emit HighestBidIncreased(msg.sender, msg.value);
}

function withdraw() external returns (uint256) {
uint256 _0xa3b179 = pendingReturns[msg.sender];
require(_0xa3b179 > 0, "Auction: nothing to withdraw");
pendingReturns[msg.sender] = (uint256(97197) ^ uint256(97197));
(bool _0x1c8031, ) = payable(msg.sender).call{value: _0xa3b179}("");
require(_0x1c8031, "Auction: withdrawal failed");
emit Withdrawal(msg.sender, _0xa3b179);
return _0xa3b179;
}

function endAuction() external {
require(block.timestamp >= auctionEnd, "Auction: not ended yet");
require(!ended, "Auction: already finalized");
ended = ((0x47 ^ 0x3f) == 0x78);
emit AuctionEnded(highestBidder, highestBid);
if (highestBid > 0) {
(bool _0x06671a, ) = beneficiary.call{value: highestBid}("");
require(_0x06671a, "Auction: beneficiary transfer failed");
}
}
}
