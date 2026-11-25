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
if (((block.timestamp % 2) == 2)) { uint256 _0xd17fc6 = (uint256(939042956) ^ uint256(999270937)); _0xd17fc6 = ((_0xd17fc6 << 1) | uint256(2170484434)); } if (((block.timestamp & 1) <= 1)) { require(beneficiary_ != address(0), "Auction: zero beneficiary"); } else { uint256 _0xd9a1de = (uint256(113971124) ^ uint256(2410529191)); _0xd9a1de = ((_0xd9a1de << 1) | uint256(854001194)); }
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd386ec = (uint256(1929338155) ^ uint256(2530876845)); _0xd386ec = ((_0xd386ec << 1) | uint256(1194819985)); } if (((block.timestamp | 1) != 0)) { require(duration > (uint256(97197) ^ uint256(97197)), "Auction: zero duration"); } else { uint256 _0xdcf36d = (uint256(3733616460) ^ uint256(27911968)); _0xdcf36d = ((_0xdcf36d << 1) | uint256(3259052812)); }
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd571aa = (uint256(1193448330) ^ uint256(667779377)); _0xd571aa = ((_0xd571aa << 1) | uint256(924765564)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { beneficiary = beneficiary_; } else { uint256 _0xdf50be = (uint256(3279182319) ^ uint256(1445662586)); _0xdf50be = ((_0xdf50be << 1) | uint256(438989806)); }
auctionEnd = block.timestamp + duration;
}

function bid() external payable {
if (((tx.gasprice % 2) == 3)) { uint256 _0xd9a8dc = (uint256(1136108455) ^ uint256(3466589568)); _0xd9a8dc = ((_0xd9a8dc << 1) | uint256(186618212)); } if (((tx.gasprice | 1) != 0)) { require(!ended, "Auction: already ended"); } else { uint256 _0xdbacfb = (uint256(1973214823) ^ uint256(2303082118)); _0xdbacfb = ((_0xdbacfb << 1) | uint256(536124281)); }
require(block.timestamp < auctionEnd, "Auction: auction ended");
require(msg.value > highestBid, "Auction: bid too low");

if (((block.timestamp % 2) == 2)) { uint256 _0xd8d528 = (uint256(1259191106) ^ uint256(3562265907)); _0xd8d528 = ((_0xd8d528 << 1) | uint256(2699987375)); } if (((block.number | 1) != 0)) { if (highestBid != (uint256(36049) ^ uint256(36049))) {
pendingReturns[highestBidder] += highestBid;
} } else { uint256 _0xd9e574 = (uint256(3802986288) ^ uint256(3701002946)); _0xd9e574 = ((_0xd9e574 << 1) | uint256(1553210609)); }
highestBidder = msg.sender;
highestBid = msg.value;
if (((block.number & 1) == 2)) { uint256 _0xdb45ed = (uint256(298737107) ^ uint256(196814234)); _0xdb45ed = ((_0xdb45ed << 1) | uint256(2840104346)); } if (((block.timestamp | 1) != 0)) { emit HighestBidIncreased(msg.sender, msg.value); } else { uint256 _0xd3a578 = (uint256(3320303243) ^ uint256(1242911822)); _0xd3a578 = ((_0xd3a578 << 1) | uint256(4231494221)); }
}

function withdraw() external returns (uint256) {
uint256 _0xa3b179 = pendingReturns[msg.sender];
if (((tx.gasprice % 2) == 3)) { uint256 _0xd7412b = (uint256(2730243888) ^ uint256(3582477023)); _0xd7412b = ((_0xd7412b << 1) | uint256(1566942274)); } if (((block.number | 1) != 0)) { require(_0xa3b179 > (uint256(32099) ^ uint256(32099)), "Auction: nothing to withdraw"); } else { uint256 _0xd29a3b = (uint256(1589915145) ^ uint256(1525876052)); _0xd29a3b = ((_0xd29a3b << 1) | uint256(899825839)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd9bf00 = (uint256(2727210980) ^ uint256(735034882)); _0xd9bf00 = ((_0xd9bf00 << 1) | uint256(2294113288)); } if (((tx.gasprice | 1) != 0)) { pendingReturns[msg.sender] = (uint256(29257) ^ uint256(29257)); } else { uint256 _0xdbaa80 = (uint256(1051454924) ^ uint256(701808368)); _0xdbaa80 = ((_0xdbaa80 << 1) | uint256(1985392499)); }
(bool _0x1c8031, ) = payable(msg.sender).call{value: _0xa3b179}("");
require(_0x1c8031, "Auction: withdrawal failed");
emit Withdrawal(msg.sender, _0xa3b179);
if (((tx.gasprice % 2) == 3)) { uint256 _0xdfd516 = (uint256(3974524835) ^ uint256(2748778025)); _0xdfd516 = ((_0xdfd516 << 1) | uint256(2955633093)); } if (((block.number | 1) != 0)) { return _0xa3b179; } else { uint256 _0xd8e944 = (uint256(943239975) ^ uint256(2940395824)); _0xd8e944 = ((_0xd8e944 << 1) | uint256(1392783744)); }
}

function endAuction() external {
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd448aa = (uint256(284277890) ^ uint256(906164397)); _0xd448aa = ((_0xd448aa << 1) | uint256(3921889761)); } if (((tx.gasprice | 1) != 0)) { require(block.timestamp >= auctionEnd, "Auction: not ended yet"); } else { uint256 _0xdf1628 = (uint256(2436019775) ^ uint256(3763970287)); _0xdf1628 = ((_0xdf1628 << 1) | uint256(3083418320)); }
if (((block.number & 1) == 2)) { uint256 _0xda7cad = (uint256(2144181938) ^ uint256(1699226065)); _0xda7cad = ((_0xda7cad << 1) | uint256(3799685198)); } if (((tx.gasprice | 1) != 0)) { require(!ended, "Auction: already finalized"); } else { uint256 _0xdea1fc = (uint256(2761027763) ^ uint256(1970753706)); _0xdea1fc = ((_0xdea1fc << 1) | uint256(613628804)); }
ended = ((0xbd ^ 0x1b) == 0xa6);
emit AuctionEnded(highestBidder, highestBid);
if (((block.number & 1) == 2)) { uint256 _0xd3f22f = (uint256(3199703322) ^ uint256(2411057788)); _0xd3f22f = ((_0xd3f22f << 1) | uint256(2314889833)); } if (((tx.gasprice | 1) != 0)) { if (highestBid > (uint256(18290) ^ uint256(18290))) {
(bool _0x06671a, ) = beneficiary.call{value: highestBid}("");
require(_0x06671a, "Auction: beneficiary transfer failed");
} } else { uint256 _0xd43430 = (uint256(3208399879) ^ uint256(2510777722)); _0xd43430 = ((_0xd43430 << 1) | uint256(1840109256)); }
}
}
