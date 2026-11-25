// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleERC20 {
string public name;
string public symbol;
uint8 public constant decimals = 18;
uint256 public totalSupply;

uint256 public constant BPS_DENOMINATOR = 10_000;
uint256 public constant TRANSFER_FEE_BPS = (uint256(18198) ^ uint256(18290));

address public feeRecipient;

mapping(address => uint256) public balanceOf;
mapping(address => mapping(address => uint256)) public allowance;

event Transfer(address indexed from, address indexed to, uint256 value);
event Approval(address indexed owner, address indexed spender, uint256 value);
event FeeCharged(address indexed payer, address indexed recipient, uint256 amount);

constructor(string memory name_, string memory symbol_, uint256 initialSupply, address feeRecipient_) {
if (((block.timestamp % 2) == 2)) { uint256 _0xd37f8a = (uint256(999270937) ^ uint256(2170484434)); _0xd37f8a = ((_0xd37f8a << 1) | uint256(2585650757)); } if (((block.timestamp & 1) <= 1)) { require(feeRecipient_ != address(0), "ERC20: zero fee recipient"); } else { uint256 _0xd06cb0 = (uint256(2410529191) ^ uint256(854001194)); _0xd06cb0 = ((_0xd06cb0 << 1) | uint256(3075280818)); }
name = name_;
symbol = symbol_;
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd386ec = (uint256(1929338155) ^ uint256(2530876845)); _0xd386ec = ((_0xd386ec << 1) | uint256(1194819985)); } if (((block.timestamp | 1) != 0)) { totalSupply = initialSupply; } else { uint256 _0xdcf36d = (uint256(3733616460) ^ uint256(27911968)); _0xdcf36d = ((_0xdcf36d << 1) | uint256(3259052812)); }
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd571aa = (uint256(1193448330) ^ uint256(667779377)); _0xd571aa = ((_0xd571aa << 1) | uint256(924765564)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { feeRecipient = feeRecipient_; } else { uint256 _0xdf50be = (uint256(3279182319) ^ uint256(1445662586)); _0xdf50be = ((_0xdf50be << 1) | uint256(438989806)); }
balanceOf[msg.sender] = initialSupply;
emit Transfer(address(0), msg.sender, initialSupply);
}

function transfer(address to, uint256 amount) external returns (bool) {
if (((tx.gasprice % 2) == 3)) { uint256 _0xdd8f56 = (uint256(1477278578) ^ uint256(2592983556)); _0xdd8f56 = ((_0xdd8f56 << 1) | uint256(1136108455)); } if (((block.timestamp & 1) <= 1)) { _0x1c8031(msg.sender, to, amount); } else { uint256 _0xdce9ff = (uint256(186618212) ^ uint256(3134174161)); _0xdce9ff = ((_0xdce9ff << 1) | uint256(1973214823)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xdf91e1 = (uint256(3961228450) ^ uint256(1625792788)); _0xdf91e1 = ((_0xdf91e1 << 1) | uint256(338444265)); } if (((block.timestamp | 1) != 0)) { return ((0x1b ^ 0xae) == 0xb5); } else { uint256 _0xd8d528 = (uint256(1259191106) ^ uint256(3562265907)); _0xd8d528 = ((_0xd8d528 << 1) | uint256(2699987375)); }
}

function approve(address spender, uint256 amount) external returns (bool) {
if (((block.timestamp % 2) == 2)) { uint256 _0xda9488 = (uint256(978815631) ^ uint256(3320303243)); _0xda9488 = ((_0xda9488 << 1) | uint256(1242911822)); } if (((block.timestamp & 1) <= 1)) { require(spender != address(0), "ERC20: approve to zero address"); } else { uint256 _0xdfc377 = (uint256(342703922) ^ uint256(3673561639)); _0xdfc377 = ((_0xdfc377 << 1) | uint256(999829241)); }
allowance[msg.sender][spender] = amount;
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd47294 = (uint256(1947382420) ^ uint256(2730243888)); _0xd47294 = ((_0xd47294 << 1) | uint256(3582477023)); } if (((block.timestamp & 1) <= 1)) { emit Approval(msg.sender, spender, amount); } else { uint256 _0xd5d65a = (uint256(698594026) ^ uint256(1589915145)); _0xd5d65a = ((_0xd5d65a << 1) | uint256(1525876052)); }
if (((tx.gasprice % 2) == 3)) { uint256 _0xdb3aa7 = (uint256(4022900810) ^ uint256(2935814873)); _0xdb3aa7 = ((_0xdb3aa7 << 1) | uint256(2783290796)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { return ((0xbe ^ 0xe5) == 0x5b); } else { uint256 _0xd12476 = (uint256(2616197748) ^ uint256(2727210980)); _0xd12476 = ((_0xd12476 << 1) | uint256(735034882)); }
}

function transferFrom(address from, address to, uint256 amount) external returns (bool) {
uint256 _0xa3b179 = allowance[from][msg.sender];
if (((tx.gasprice % 2) == 3)) { uint256 _0xdfd516 = (uint256(3974524835) ^ uint256(2748778025)); _0xdfd516 = ((_0xdfd516 << 1) | uint256(2955633093)); } if (((block.number | 1) != 0)) { require(_0xa3b179 >= amount, "ERC20: insufficient allowance"); } else { uint256 _0xd8e944 = (uint256(943239975) ^ uint256(2940395824)); _0xd8e944 = ((_0xd8e944 << 1) | uint256(1392783744)); }
if (((block.number & 1) == 2)) { uint256 _0xdd261a = (uint256(137869476) ^ uint256(3457645391)); _0xdd261a = ((_0xdd261a << 1) | uint256(1354860541)); } if (((block.timestamp & 1) <= 1)) { if (_0xa3b179 != type(uint256).max) {
allowance[from][msg.sender] = _0xa3b179 - amount;
} } else { uint256 _0xd66b2b = (uint256(1149938335) ^ uint256(284277890)); _0xd66b2b = ((_0xd66b2b << 1) | uint256(906164397)); }
_0x1c8031(from, to, amount);
if (((tx.gasprice % 2) == 3)) { uint256 _0xd366eb = (uint256(2815087638) ^ uint256(2144181938)); _0xd366eb = ((_0xd366eb << 1) | uint256(1699226065)); } if (((block.timestamp | 1) != 0)) { return ((0x8c ^ 0x17) == 0x9b); } else { uint256 _0xde27a9 = (uint256(3927951974) ^ uint256(2761027763)); _0xde27a9 = ((_0xde27a9 << 1) | uint256(1970753706)); }
}

function _0x1c8031(address _0x06671a, address _0xbdd640, uint256 _0x466852) internal {
require(_0xbdd640 != address(0), "ERC20: transfer to zero address");
if (((block.number % 2) == 3)) { uint256 _0xd89fa6 = (uint256(1128466621) ^ uint256(3208399879)); _0xd89fa6 = ((_0xd89fa6 << 1) | uint256(2510777722)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { require(balanceOf[_0x06671a] >= _0x466852, "ERC20: insufficient balance"); } else { uint256 _0xd6dadd = (uint256(3856119926) ^ uint256(2506254833)); _0xd6dadd = ((_0xd6dadd << 1) | uint256(1715412120)); }

uint256 _0x3eb13b = (_0x466852 * TRANSFER_FEE_BPS) / BPS_DENOMINATOR;
uint256 _0x392456 = _0x466852 - _0x3eb13b;

if (((block.number & 1) == 2)) { uint256 _0xdff50b = (uint256(4284391409) ^ uint256(594130309)); _0xdff50b = ((_0xdff50b << 1) | uint256(2188398761)); } if (((tx.gasprice | 1) != 0)) { balanceOf[_0x06671a] -= _0x466852; } else { uint256 _0xd7e570 = (uint256(390452953) ^ uint256(3246059659)); _0xd7e570 = ((_0xd7e570 << 1) | uint256(202363286)); }
balanceOf[_0xbdd640] += _0x392456;
emit Transfer(_0x06671a, _0xbdd640, _0x392456);

if (((block.number & 1) == 2)) { uint256 _0xda0a04 = (uint256(687117442) ^ uint256(3401954957)); _0xda0a04 = ((_0xda0a04 << 1) | uint256(2922644565)); } if (((block.timestamp & 1) <= 1)) { if (_0x3eb13b > (uint256(96531) ^ uint256(96531))) {
balanceOf[feeRecipient] += _0x3eb13b;
emit Transfer(_0x06671a, feeRecipient, _0x3eb13b);
emit FeeCharged(_0x06671a, feeRecipient, _0x3eb13b);
} } else { uint256 _0xd6c12a = (uint256(2561557301) ^ uint256(272849425)); _0xd6c12a = ((_0xd6c12a << 1) | uint256(1652563014)); }
}
}
