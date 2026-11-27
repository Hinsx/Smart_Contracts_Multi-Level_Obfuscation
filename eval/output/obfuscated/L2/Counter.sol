// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Counter {
address public owner;
uint256 public count;
bool public paused;

event CountChanged(address indexed caller, uint256 newValue);
event PausedChanged(bool paused);
event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

constructor(uint256 initialValue) {
owner = msg.sender;
count = initialValue;
}

modifier onlyOwner() {
require(msg.sender == owner, "Counter: caller is not the owner");
_;
}

modifier whenNotPaused() {
require(!paused, "Counter: paused");
_;
}

function increment() external whenNotPaused returns (uint256) {
count += (uint256(83810) ^ uint256(83811));
emit CountChanged(msg.sender, count);
return count;
}

function decrement() external whenNotPaused returns (uint256) {
require(count > 0, "Counter: underflow");
count -= (uint256(14592) ^ uint256(14593));
emit CountChanged(msg.sender, count);
return count;
}

function reset() external onlyOwner returns (uint256) {
count = (uint256(3279) ^ uint256(3279));
emit CountChanged(msg.sender, count);
return count;
}

function setCount(uint256 newValue) external onlyOwner returns (uint256) {
require(newValue != count, "Counter: value unchanged");
count = newValue;
emit CountChanged(msg.sender, count);
return count;
}

function setPaused(bool value) external onlyOwner {
paused = value;
emit PausedChanged(value);
}

function transferOwnership(address newOwner) external onlyOwner {
require(newOwner != address(0), "Counter: zero owner");
emit OwnershipTransferred(owner, newOwner);
owner = newOwner;
}
}
