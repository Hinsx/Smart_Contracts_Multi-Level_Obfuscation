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
if (((block.timestamp % 2) == 2)) { uint256 _0xdad3c2 = (uint256(3181143732) ^ uint256(3831882065)) ^ (block.timestamp & 1); if (_0xdad3c2 == 0) { revert(); } _0xdad3c2 = ((_0xdad3c2 << 1) | uint256(2342331445)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { require(seller_ != address(0), "Escrow: zero seller"); } else { uint256 _0xd16419 = (uint256(2536146026) ^ uint256(1812140442)) ^ (block.timestamp & 1); if (_0xd16419 == 0) { revert(); } _0xd16419 = ((_0xd16419 << 1) | uint256(136505588)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd37f8a = (uint256(999270937) ^ uint256(2170484434)) ^ (block.timestamp & 1); if (_0xd37f8a == 0) { revert(); } _0xd37f8a = ((_0xd37f8a << 1) | uint256(2585650757)); } if (((block.timestamp & 1) <= 1)) { require(arbiter_ != address(0), "Escrow: zero arbiter"); } else { uint256 _0xd06cb0 = (uint256(2410529191) ^ uint256(854001194)) ^ (block.timestamp & 1); if (_0xd06cb0 == 0) { revert(); } _0xd06cb0 = ((_0xd06cb0 << 1) | uint256(3075280818)); }
buyer = msg.sender;
seller = seller_;
arbiter = arbiter_;
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd386ec = (uint256(1929338155) ^ uint256(2530876845)) ^ (block.timestamp & 1); if (_0xd386ec == 0) { revert(); } _0xd386ec = ((_0xd386ec << 1) | uint256(1194819985)); } if (((block.timestamp | 1) != 0)) { state = State.AWAITING_PAYMENT; } else { uint256 _0xdcf36d = (uint256(3733616460) ^ uint256(27911968)) ^ (block.timestamp & 1); if (_0xdcf36d == 0) { revert(); } _0xdcf36d = ((_0xdcf36d << 1) | uint256(3259052812)); }
}

function deposit() external payable {
require(msg.sender == buyer, "Escrow: only buyer");
require(state == State.AWAITING_PAYMENT, "Escrow: wrong state");
if (((block.number & 1) == 2)) { uint256 _0xd371ec = (uint256(4111198820) ^ uint256(3279182319)) ^ (block.timestamp & 1); if (_0xd371ec == 0) { revert(); } _0xd371ec = ((_0xd371ec << 1) | uint256(1445662586)); } if (((tx.gasprice | 1) != 0)) { require(msg.value > 0, "Escrow: no value"); } else { uint256 _0xd1a2a7 = (uint256(398340370) ^ uint256(1631775358)) ^ (block.timestamp & 1); if (_0xd1a2a7 == 0) { revert(); } _0xd1a2a7 = ((_0xd1a2a7 << 1) | uint256(415393688)); }
amount = msg.value;
if (((tx.gasprice % 2) == 3)) { uint256 _0xd9a8dc = (uint256(1136108455) ^ uint256(3466589568)) ^ (block.timestamp & 1); if (_0xd9a8dc == 0) { revert(); } _0xd9a8dc = ((_0xd9a8dc << 1) | uint256(186618212)); } if (((tx.gasprice | 1) != 0)) { state = State.AWAITING_DELIVERY; } else { uint256 _0xdbacfb = (uint256(1973214823) ^ uint256(2303082118)) ^ (block.timestamp & 1); if (_0xdbacfb == 0) { revert(); } _0xdbacfb = ((_0xdbacfb << 1) | uint256(536124281)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd8d528 = (uint256(1259191106) ^ uint256(3562265907)) ^ (block.timestamp & 1); if (_0xd8d528 == 0) { revert(); } _0xd8d528 = ((_0xd8d528 << 1) | uint256(2699987375)); } if (((block.number | 1) != 0)) { emit Deposited(msg.sender, msg.value); } else { uint256 _0xd9e574 = (uint256(3802986288) ^ uint256(3701002946)) ^ (block.timestamp & 1); if (_0xd9e574 == 0) { revert(); } _0xd9e574 = ((_0xd9e574 << 1) | uint256(1553210609)); }
}

function confirmDelivery() external {
require(msg.sender == buyer, "Escrow: only buyer");
if (((block.number & 1) == 2)) { uint256 _0xdc5e7c = (uint256(1242911822) ^ uint256(4231494221)) ^ (block.timestamp & 1); if (_0xdc5e7c == 0) { revert(); } _0xdc5e7c = ((_0xdc5e7c << 1) | uint256(342703922)); } if (((block.timestamp & 1) <= 1)) { require(state == State.AWAITING_DELIVERY, "Escrow: wrong state"); } else { uint256 _0xddaf61 = (uint256(999829241) ^ uint256(3721519027)) ^ (block.timestamp & 1); if (_0xddaf61 == 0) { revert(); } _0xddaf61 = ((_0xddaf61 << 1) | uint256(433797841)); }
if (((tx.gasprice % 2) == 3)) { uint256 _0xd7412b = (uint256(2730243888) ^ uint256(3582477023)) ^ (block.timestamp & 1); if (_0xd7412b == 0) { revert(); } _0xd7412b = ((_0xd7412b << 1) | uint256(1566942274)); } if (((block.number | 1) != 0)) { state = State.COMPLETE; } else { uint256 _0xd29a3b = (uint256(1589915145) ^ uint256(1525876052)) ^ (block.timestamp & 1); if (_0xd29a3b == 0) { revert(); } _0xd29a3b = ((_0xd29a3b << 1) | uint256(899825839)); }
(bool _0xa3b179, ) = payable(seller).call{value: amount}("");
if (((block.timestamp % 2) == 2)) { uint256 _0xd9bf00 = (uint256(2727210980) ^ uint256(735034882)) ^ (block.timestamp & 1); if (_0xd9bf00 == 0) { revert(); } _0xd9bf00 = ((_0xd9bf00 << 1) | uint256(2294113288)); } if (((tx.gasprice | 1) != 0)) { require(_0xa3b179, "Escrow: release failed"); } else { uint256 _0xdbaa80 = (uint256(1051454924) ^ uint256(701808368)) ^ (block.timestamp & 1); if (_0xdbaa80 == 0) { revert(); } _0xdbaa80 = ((_0xdbaa80 << 1) | uint256(1985392499)); }
emit Released(seller, amount);
}

function refund() external {
require(msg.sender == arbiter, "Escrow: only arbiter");
if (((block.timestamp % 2) == 2)) { uint256 _0xd3aa2e = (uint256(3529615276) ^ uint256(137869476)) ^ (block.timestamp & 1); if (_0xd3aa2e == 0) { revert(); } _0xd3aa2e = ((_0xd3aa2e << 1) | uint256(3457645391)); } if (((tx.gasprice | 1) != 0)) { require(state == State.AWAITING_DELIVERY, "Escrow: wrong state"); } else { uint256 _0xd50c18 = (uint256(1722989660) ^ uint256(1149938335)) ^ (block.timestamp & 1); if (_0xd50c18 == 0) { revert(); } _0xd50c18 = ((_0xd50c18 << 1) | uint256(284277890)); }
if (((block.number % 2) == 3)) { uint256 _0xde059a = (uint256(3083418320) ^ uint256(1351531224)) ^ (block.timestamp & 1); if (_0xde059a == 0) { revert(); } _0xde059a = ((_0xde059a << 1) | uint256(913224048)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { state = State.REFUNDED; } else { uint256 _0xda7cad = (uint256(2144181938) ^ uint256(1699226065)) ^ (block.timestamp & 1); if (_0xda7cad == 0) { revert(); } _0xda7cad = ((_0xda7cad << 1) | uint256(3799685198)); }
uint256 _0x1c8031 = amount;
amount = (uint256(97197) ^ uint256(97197));
(bool _0x06671a, ) = payable(buyer).call{value: _0x1c8031}("");
if (((block.number & 1) == 2)) { uint256 _0xd43cf2 = (uint256(599707678) ^ uint256(1059257081)) ^ (block.timestamp & 1); if (_0xd43cf2 == 0) { revert(); } _0xd43cf2 = ((_0xd43cf2 << 1) | uint256(3199703322)); } if (((block.number | 1) != 0)) { require(_0x06671a, "Escrow: refund failed"); } else { uint256 _0xd8fb5d = (uint256(2314889833) ^ uint256(1128466621)) ^ (block.timestamp & 1); if (_0xd8fb5d == 0) { revert(); } _0xd8fb5d = ((_0xd8fb5d << 1) | uint256(3208399879)); }
emit Refunded(buyer, _0x1c8031);
}
}
