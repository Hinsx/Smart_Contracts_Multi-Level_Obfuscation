// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SimpleAuction
/// @notice Time-bounded auction with refund tracking, modelled after the Solidity docs example.
/// @dev Single file, no imports. Time is read from block.timestamp so tests must time-travel.
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
        uint256 amount = pendingReturns[msg.sender];
        require(amount > 0, "Auction: nothing to withdraw");
        pendingReturns[msg.sender] = 0;
        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        require(ok, "Auction: withdrawal failed");
        emit Withdrawal(msg.sender, amount);
        return amount;
    }

    function endAuction() external {
        require(block.timestamp >= auctionEnd, "Auction: not ended yet");
        require(!ended, "Auction: already finalized");
        ended = true;
        emit AuctionEnded(highestBidder, highestBid);
        if (highestBid > 0) {
            (bool ok, ) = beneficiary.call{value: highestBid}("");
            require(ok, "Auction: beneficiary transfer failed");
        }
    }
}
