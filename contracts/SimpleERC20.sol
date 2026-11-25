// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SimpleERC20
/// @notice ERC20 subset with a fixed 1% transfer fee credited to a fee recipient.
/// @dev Single file, no imports. Deliberately keeps public state-variable getters,
///      events, mappings and constants so the layout pass has something to protect.
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
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        require(spender != address(0), "ERC20: approve to zero address");
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        require(allowed >= amount, "ERC20: insufficient allowance");
        if (allowed != type(uint256).max) {
            allowance[from][msg.sender] = allowed - amount;
        }
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(to != address(0), "ERC20: transfer to zero address");
        require(balanceOf[from] >= amount, "ERC20: insufficient balance");

        uint256 fee = (amount * TRANSFER_FEE_BPS) / BPS_DENOMINATOR;
        uint256 net = amount - fee;

        balanceOf[from] -= amount;
        balanceOf[to] += net;
        emit Transfer(from, to, net);

        if (fee > 0) {
            balanceOf[feeRecipient] += fee;
            emit Transfer(from, feeRecipient, fee);
            emit FeeCharged(from, feeRecipient, fee);
        }
    }
}
