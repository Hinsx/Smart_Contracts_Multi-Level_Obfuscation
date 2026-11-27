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
if (((block.timestamp % 2) == 2)) { uint256 _0xd972a8 = (uint256(1812140442) ^ uint256(136505588)) ^ (block.timestamp & 1); if (_0xd972a8 == 0) { revert(); } _0xd972a8 = ((_0xd972a8 << 1) | uint256(127978095)); } if (((block.timestamp | 1) != 0)) { require(beneficiary_ != address(0), "Auction: zero beneficiary"); } else { uint256 _0xd17fc6 = (uint256(939042956) ^ uint256(999270937)) ^ (block.timestamp & 1); if (_0xd17fc6 == 0) { revert(); } _0xd17fc6 = ((_0xd17fc6 << 1) | uint256(2170484434)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd8fadc = (uint256(854001194) ^ uint256(3075280818)) ^ (block.timestamp & 1); if (_0xd8fadc == 0) { revert(); } _0xd8fadc = ((_0xd8fadc << 1) | uint256(2791232394)); } if (((block.timestamp | 1) != 0)) { require(duration > 0, "Auction: zero duration"); } else { uint256 _0xdb38a0 = (uint256(2340505847) ^ uint256(1801823909)) ^ (block.timestamp & 1); if (_0xdb38a0 == 0) { revert(); } _0xdb38a0 = ((_0xdb38a0 << 1) | uint256(946785249)); }
if (((block.number % 2) == 3)) { uint256 _0xd47378 = (uint256(3476477324) ^ uint256(3733616460)) ^ (block.timestamp & 1); if (_0xd47378 == 0) { revert(); } _0xd47378 = ((_0xd47378 << 1) | uint256(27911968)); } if (((block.number | 1) != 0)) { beneficiary = beneficiary_; } else { uint256 _0xdc2413 = (uint256(3460967358) ^ uint256(685731525)) ^ (block.timestamp & 1); if (_0xdc2413 == 0) { revert(); } _0xdc2413 = ((_0xdc2413 << 1) | uint256(2998485883)); }
auctionEnd = block.timestamp + duration;
}

function bid() external payable {
require(!ended, "Auction: already ended");
require(block.timestamp < auctionEnd, "Auction: auction ended");
if (((block.number & 1) == 2)) { uint256 _0xdf50be = (uint256(3279182319) ^ uint256(1445662586)) ^ (block.timestamp & 1); if (_0xdf50be == 0) { revert(); } _0xdf50be = ((_0xdf50be << 1) | uint256(438989806)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { require(msg.value > highestBid, "Auction: bid too low"); } else { uint256 _0xd17be3 = (uint256(1631775358) ^ uint256(415393688)) ^ (block.timestamp & 1); if (_0xd17be3 == 0) { revert(); } _0xd17be3 = ((_0xd17be3 << 1) | uint256(1541804687)); }

if (((block.number % 2) == 3)) { uint256 _0xd43b7a = (uint256(3466589568) ^ uint256(186618212)) ^ (block.timestamp & 1); if (_0xd43b7a == 0) { revert(); } _0xd43b7a = ((_0xd43b7a << 1) | uint256(3134174161)); } if (((tx.gasprice | 1) != 0)) { if (highestBid != 0) {
pendingReturns[highestBidder] += highestBid;
} } else { uint256 _0xd759cd = (uint256(2303082118) ^ uint256(536124281)) ^ (block.timestamp & 1); if (_0xd759cd == 0) { revert(); } _0xd759cd = ((_0xd759cd << 1) | uint256(4179500365)); }
highestBidder = msg.sender;
if (((block.timestamp % 2) == 2)) { uint256 _0xd8d528 = (uint256(1259191106) ^ uint256(3562265907)) ^ (block.timestamp & 1); if (_0xd8d528 == 0) { revert(); } _0xd8d528 = ((_0xd8d528 << 1) | uint256(2699987375)); } if (((block.number | 1) != 0)) { highestBid = msg.value; } else { uint256 _0xd9e574 = (uint256(3802986288) ^ uint256(3701002946)) ^ (block.timestamp & 1); if (_0xd9e574 == 0) { revert(); } _0xd9e574 = ((_0xd9e574 << 1) | uint256(1553210609)); }
emit HighestBidIncreased(msg.sender, msg.value);
}

function withdraw() external returns (uint256) {
uint256 _0xa3b179 = pendingReturns[msg.sender];
require(_0xa3b179 > 0, "Auction: nothing to withdraw");
if (((block.timestamp % 2) == 2)) { uint256 _0xda9488 = (uint256(978815631) ^ uint256(3320303243)) ^ (block.timestamp & 1); if (_0xda9488 == 0) { revert(); } _0xda9488 = ((_0xda9488 << 1) | uint256(1242911822)); } if (((block.timestamp & 1) <= 1)) { pendingReturns[msg.sender] = (uint256(97197) ^ uint256(97197)); } else { uint256 _0xdfc377 = (uint256(342703922) ^ uint256(3673561639)) ^ (block.timestamp & 1); if (_0xdfc377 == 0) { revert(); } _0xdfc377 = ((_0xdfc377 << 1) | uint256(999829241)); }
(bool _0x1c8031, ) = payable(msg.sender).call{value: _0xa3b179}("");
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd47294 = (uint256(1947382420) ^ uint256(2730243888)) ^ (block.timestamp & 1); if (_0xd47294 == 0) { revert(); } _0xd47294 = ((_0xd47294 << 1) | uint256(3582477023)); } if (((block.timestamp & 1) <= 1)) { require(_0x1c8031, "Auction: withdrawal failed"); } else { uint256 _0xd5d65a = (uint256(698594026) ^ uint256(1589915145)) ^ (block.timestamp & 1); if (_0xd5d65a == 0) { revert(); } _0xd5d65a = ((_0xd5d65a << 1) | uint256(1525876052)); }
emit Withdrawal(msg.sender, _0xa3b179);
if (((tx.gasprice % 2) == 3)) { uint256 _0xdb3aa7 = (uint256(4022900810) ^ uint256(2935814873)) ^ (block.timestamp & 1); if (_0xdb3aa7 == 0) { revert(); } _0xdb3aa7 = ((_0xdb3aa7 << 1) | uint256(2783290796)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { return _0xa3b179; } else { uint256 _0xd12476 = (uint256(2616197748) ^ uint256(2727210980)) ^ (block.timestamp & 1); if (_0xd12476 == 0) { revert(); } _0xd12476 = ((_0xd12476 << 1) | uint256(735034882)); }
}

function endAuction() external {
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd451b4 = (uint256(4249970407) ^ uint256(3974524835)) ^ (block.timestamp & 1); if (_0xd451b4 == 0) { revert(); } _0xd451b4 = ((_0xd451b4 << 1) | uint256(2748778025)); } if (((block.number | 1) != 0)) { require(block.timestamp >= auctionEnd, "Auction: not ended yet"); } else { uint256 _0xdb02b6 = (uint256(2392080954) ^ uint256(943239975)) ^ (block.timestamp & 1); if (_0xdb02b6 == 0) { revert(); } _0xdb02b6 = ((_0xdb02b6 << 1) | uint256(2940395824)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd3aa2e = (uint256(3529615276) ^ uint256(137869476)) ^ (block.timestamp & 1); if (_0xd3aa2e == 0) { revert(); } _0xd3aa2e = ((_0xd3aa2e << 1) | uint256(3457645391)); } if (((tx.gasprice | 1) != 0)) { require(!ended, "Auction: already finalized"); } else { uint256 _0xd50c18 = (uint256(1722989660) ^ uint256(1149938335)) ^ (block.timestamp & 1); if (_0xd50c18 == 0) { revert(); } _0xd50c18 = ((_0xd50c18 << 1) | uint256(284277890)); }
ended = ((0x47 ^ 0x3f) == 0x78);
emit AuctionEnded(highestBidder, highestBid);
if (((block.number % 2) == 3)) { uint256 _0xde059a = (uint256(3083418320) ^ uint256(1351531224)) ^ (block.timestamp & 1); if (_0xde059a == 0) { revert(); } _0xde059a = ((_0xde059a << 1) | uint256(913224048)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { if (highestBid > 0) {
(bool _0x06671a, ) = beneficiary.call{value: highestBid}("");
require(_0x06671a, "Auction: beneficiary transfer failed");
} } else { uint256 _0xda7cad = (uint256(2144181938) ^ uint256(1699226065)) ^ (block.timestamp & 1); if (_0xda7cad == 0) { revert(); } _0xda7cad = ((_0xda7cad << 1) | uint256(3799685198)); }
}
}
