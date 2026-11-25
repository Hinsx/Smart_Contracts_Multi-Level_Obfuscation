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
if (((block.number % 2) == 3)) { uint256 _0xd16419 = (uint256(2536146026) ^ uint256(1812140442)); _0xd16419 = ((_0xd16419 << 1) | uint256(136505588)); } if (((block.timestamp & 1) <= 1)) { require(seller_ != address(0), "Escrow: zero seller"); } else { uint256 _0xd07a0c = (uint256(402418011) ^ uint256(939042956)); _0xd07a0c = ((_0xd07a0c << 1) | uint256(999270937)); }
if (((block.number % 2) == 3)) { uint256 _0xd06cb0 = (uint256(2410529191) ^ uint256(854001194)); _0xd06cb0 = ((_0xd06cb0 << 1) | uint256(3075280818)); } if (((block.timestamp | 1) != 0)) { require(arbiter_ != address(0), "Escrow: zero arbiter"); } else { uint256 _0xda65ed = (uint256(3012167821) ^ uint256(2340505847)); _0xda65ed = ((_0xda65ed << 1) | uint256(1801823909)); }
buyer = msg.sender;
seller = seller_;
arbiter = arbiter_;
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd96da1 = (uint256(1194819985) ^ uint256(3476477324)); _0xd96da1 = ((_0xd96da1 << 1) | uint256(3733616460)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { state = State.AWAITING_PAYMENT; } else { uint256 _0xd01a9e = (uint256(3259052812) ^ uint256(3460967358)); _0xd01a9e = ((_0xd01a9e << 1) | uint256(685731525)); }
}

function deposit() external payable {
require(msg.sender == buyer, "Escrow: only buyer");
require(state == State.AWAITING_PAYMENT, "Escrow: wrong state");
if (((block.number & 1) == 2)) { uint256 _0xdf50be = (uint256(3279182319) ^ uint256(1445662586)); _0xdf50be = ((_0xdf50be << 1) | uint256(438989806)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { require(msg.value > (uint256(97197) ^ uint256(97197)), "Escrow: no value"); } else { uint256 _0xd17be3 = (uint256(1631775358) ^ uint256(415393688)); _0xd17be3 = ((_0xd17be3 << 1) | uint256(1541804687)); }
if (((block.number % 2) == 3)) { uint256 _0xd43b7a = (uint256(3466589568) ^ uint256(186618212)); _0xd43b7a = ((_0xd43b7a << 1) | uint256(3134174161)); } if (((tx.gasprice | 1) != 0)) { amount = msg.value; } else { uint256 _0xd759cd = (uint256(2303082118) ^ uint256(536124281)); _0xd759cd = ((_0xd759cd << 1) | uint256(4179500365)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd8d528 = (uint256(1259191106) ^ uint256(3562265907)); _0xd8d528 = ((_0xd8d528 << 1) | uint256(2699987375)); } if (((block.number | 1) != 0)) { state = State.AWAITING_DELIVERY; } else { uint256 _0xd9e574 = (uint256(3802986288) ^ uint256(3701002946)); _0xd9e574 = ((_0xd9e574 << 1) | uint256(1553210609)); }
emit Deposited(msg.sender, msg.value);
}

function confirmDelivery() external {
require(msg.sender == buyer, "Escrow: only buyer");
if (((block.number & 1) == 2)) { uint256 _0xdc5e7c = (uint256(1242911822) ^ uint256(4231494221)); _0xdc5e7c = ((_0xdc5e7c << 1) | uint256(342703922)); } if (((block.timestamp & 1) <= 1)) { require(state == State.AWAITING_DELIVERY, "Escrow: wrong state"); } else { uint256 _0xddaf61 = (uint256(999829241) ^ uint256(3721519027)); _0xddaf61 = ((_0xddaf61 << 1) | uint256(433797841)); }
if (((tx.gasprice % 2) == 3)) { uint256 _0xd7412b = (uint256(2730243888) ^ uint256(3582477023)); _0xd7412b = ((_0xd7412b << 1) | uint256(1566942274)); } if (((block.number | 1) != 0)) { state = State.COMPLETE; } else { uint256 _0xd29a3b = (uint256(1589915145) ^ uint256(1525876052)); _0xd29a3b = ((_0xd29a3b << 1) | uint256(899825839)); }
(bool _0xa3b179, ) = payable(seller).call{value: amount}("");
if (((block.timestamp % 2) == 2)) { uint256 _0xd9bf00 = (uint256(2727210980) ^ uint256(735034882)); _0xd9bf00 = ((_0xd9bf00 << 1) | uint256(2294113288)); } if (((tx.gasprice | 1) != 0)) { require(_0xa3b179, "Escrow: release failed"); } else { uint256 _0xdbaa80 = (uint256(1051454924) ^ uint256(701808368)); _0xdbaa80 = ((_0xdbaa80 << 1) | uint256(1985392499)); }
emit Released(seller, amount);
}

function refund() external {
require(msg.sender == arbiter, "Escrow: only arbiter");
if (((block.timestamp % 2) == 2)) { uint256 _0xd3aa2e = (uint256(3529615276) ^ uint256(137869476)); _0xd3aa2e = ((_0xd3aa2e << 1) | uint256(3457645391)); } if (((tx.gasprice | 1) != 0)) { require(state == State.AWAITING_DELIVERY, "Escrow: wrong state"); } else { uint256 _0xd50c18 = (uint256(1722989660) ^ uint256(1149938335)); _0xd50c18 = ((_0xd50c18 << 1) | uint256(284277890)); }
if (((block.number % 2) == 3)) { uint256 _0xde059a = (uint256(3083418320) ^ uint256(1351531224)); _0xde059a = ((_0xde059a << 1) | uint256(913224048)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { state = State.REFUNDED; } else { uint256 _0xda7cad = (uint256(2144181938) ^ uint256(1699226065)); _0xda7cad = ((_0xda7cad << 1) | uint256(3799685198)); }
uint256 _0x1c8031 = amount;
amount = (uint256(36049) ^ uint256(36049));
(bool _0x06671a, ) = payable(buyer).call{value: _0x1c8031}("");
if (((block.number & 1) == 2)) { uint256 _0xd43cf2 = (uint256(599707678) ^ uint256(1059257081)); _0xd43cf2 = ((_0xd43cf2 << 1) | uint256(3199703322)); } if (((block.number | 1) != 0)) { require(_0x06671a, "Escrow: refund failed"); } else { uint256 _0xd8fb5d = (uint256(2314889833) ^ uint256(1128466621)); _0xd8fb5d = ((_0xd8fb5d << 1) | uint256(3208399879)); }
emit Refunded(buyer, _0x1c8031);
}
}
