// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleERC20 {
string public name;
string public symbol;
uint8 public constant decimals = 18;
uint256 public totalSupply;

uint256 public constant BPS_DENOMINATOR = 10_000;
uint256 public constant TRANSFER_FEE_BPS = 100;

address public feeRecipient;

mapping(address => uint256) public balanceOf;
mapping(address => mapping(address => uint256)) public allowance;

event Transfer(address indexed from, address indexed to, uint256 value);
event Approval(address indexed owner, address indexed spender, uint256 value);
event FeeCharged(address indexed payer, address indexed recipient, uint256 amount);

constructor(string memory name_, string memory symbol_, uint256 initialSupply, address feeRecipient_) {
require(feeRecipient_ != address(0), "ERC20: zero fee recipient");
name = name_;
symbol = symbol_;
totalSupply = initialSupply;
feeRecipient = feeRecipient_;
balanceOf[msg.sender] = initialSupply;
emit Transfer(address(0), msg.sender, initialSupply);
}

function transfer(address to, uint256 amount) external returns (bool) {
_0x1c8031(msg.sender, to, amount);
return true;
}

function approve(address spender, uint256 amount) external returns (bool) {
require(spender != address(0), "ERC20: approve to zero address");
allowance[msg.sender][spender] = amount;
emit Approval(msg.sender, spender, amount);
return true;
}

function transferFrom(address from, address to, uint256 amount) external returns (bool) {
uint256 _0xa3b179 = allowance[from][msg.sender];
require(_0xa3b179 >= amount, "ERC20: insufficient allowance");
if (_0xa3b179 != type(uint256).max) {
allowance[from][msg.sender] = _0xa3b179 - amount;
}
_0x1c8031(from, to, amount);
return true;
}

function _0x1c8031(address _0x06671a, address _0xbdd640, uint256 _0x466852) internal {
require(_0xbdd640 != address(0), "ERC20: transfer to zero address");
require(balanceOf[_0x06671a] >= _0x466852, "ERC20: insufficient balance");

uint256 _0x3eb13b = (_0x466852 * TRANSFER_FEE_BPS) / BPS_DENOMINATOR;
uint256 _0x392456 = _0x466852 - _0x3eb13b;

balanceOf[_0x06671a] -= _0x466852;
balanceOf[_0xbdd640] += _0x392456;
emit Transfer(_0x06671a, _0xbdd640, _0x392456);

if (_0x3eb13b > 0) {
balanceOf[feeRecipient] += _0x3eb13b;
emit Transfer(_0x06671a, feeRecipient, _0x3eb13b);
emit FeeCharged(_0x06671a, feeRecipient, _0x3eb13b);
}
}
}
