/**
 *Submitted for verification at Etherscan.io on 2025-03-18
*/

// File: contracts/interfaces/IBlobstreamO.sol


pragma solidity ^0.8.0;

struct OracleAttestationData {
    bytes32 queryId;
    ReportData report;
    uint256 attestationTimestamp; //timestamp of validatorSignatures on report
}

struct ReportData {
    bytes value;
    uint256 timestamp; //timestamp of reporter signature aggregation
    uint256 aggregatePower;
    uint256 previousTimestamp;
    uint256 nextTimestamp;
    uint256 lastConsensusTimestamp;
}

struct Signature {
    uint8 v;
    bytes32 r;
    bytes32 s;
}

struct Validator {
    address addr;
    uint256 power;
}

interface IBlobstreamO {
    function guardian() external view returns (address);
    function powerThreshold() external view returns (uint256);
    function unbondingPeriod() external view returns (uint256);
    function validatorTimestamp() external view returns (uint256);
    function verifyOracleData(
        OracleAttestationData calldata _attestData,
        Validator[] calldata _currentValidatorSet,
        Signature[] calldata _sigs
    ) external view;
}
// File: contracts/interfaces/ITellorFlex.sol


pragma solidity ^0.8.0;

interface ITellorFlex {
    function getDataBefore(bytes32 _queryId, uint256 _timestamp) external view returns (bool _ifRetrieve, bytes memory _value, uint256 _timestampRetrieved);
    function getIndexForDataBefore(bytes32 _queryId, uint256 _timestamp) external view returns (bool _found, uint256 _index);
    function getNewValueCountbyQueryId(bytes32 _queryId) external view returns (uint256);
    function getReporterByTimestamp(bytes32 _queryId, uint256 _timestamp) external view returns (address);
    function getTimestampbyQueryIdandIndex(bytes32 _queryId, uint256 _index) external view returns (uint256);
    function getTimeOfLastNewValue() external view returns (uint256);
    function isInDispute(bytes32 _queryId,uint256 _timestamp) external view returns (bool);
    function retrieveData(bytes32 _queryId, uint256 _timestamp) external view returns (bytes memory);
    function verify() external pure returns (uint256);
    function getNewValueCountbyQueryId() external view returns (uint256);
}

// File: contracts/interfaces/ITellorMaster.sol


pragma solidity ^0.8.0;

interface ITellorMaster {
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function getUintVar(bytes32 _data) external view returns (uint256);
    function mintToOracle() external;
    function totalSupply() external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}
// File: contracts/token-bridge/LayerTransition.sol


pragma solidity 0.8.19;



/// @title LayerTransition.
/// @dev The contract that enables users of really old tellor to keep using it (e.g. Liquity)
/// by forwarding calls to the Ethereum oracle contract
/// also disables all further changes of the oracle address for time based rewards
contract LayerTransition {
    /*Storage*/
    bytes32 updateOracleQueryId = keccak256(abi.encode("TellorOracleAddress", abi.encode(bytes(""))));
    ITellorMaster public token;
    ITellorFlex public tellorFlex;

    /*Functions*/
    /// @notice constructor
    /// @param _tellorFlex address of current tellor360 oracle contract
    /// @param _token address of the tellor token (tellorMaster)
    constructor(address _tellorFlex, address _token) {
        tellorFlex = ITellorFlex(_tellorFlex);
        token = ITellorMaster(_token);
    }

    /// @notice this is needed because it's called when calling mintToOracle.  We hijack it to keep it in the bridge
    /// @param _amount the amount of staking rewards to add to the token contract
    function addStakingRewards(uint256 _amount) external {
        token.transferFrom(msg.sender, address(this), _amount);
    }

    /// @notice This forwards getDataBefore calls to the old tellorFlex
    /// we're hijacking it a bit to disable further oracle updates
    /// @param _queryId queryId of interest
    /// @param _timestamp timestamp you want data to be older than
    function getDataBefore(bytes32 _queryId, uint256 _timestamp) external view returns(
        bool _ifRetrieve,
        bytes memory _value,
        uint256 _timestampRetrieved
    ) {
        if (_queryId == updateOracleQueryId) {
            return (true, abi.encode(address(this)), block.timestamp);
        }
        return tellorFlex.getDataBefore(_queryId, _timestamp);
    }

    /// @notice This forwards getIndexForDataBefore calls to the old tellorFlex
    /// @param _queryId queryId of interest
    /// @param _timestamp timestamp you want data for
    function getIndexForDataBefore(bytes32 _queryId, uint256 _timestamp) external view returns(bool _found, uint256 _index) {
        return tellorFlex.getIndexForDataBefore(_queryId, _timestamp);
    }

    /// @notice This forwards getNewValueCountbyQueryId calls to the old tellorFlex
    /// @param _queryId queryId of interest
    function getNewValueCountbyQueryId(bytes32 _queryId) external view returns(uint256) {
        return tellorFlex.getNewValueCountbyQueryId(_queryId);
    }

    /// @notice This forwards getReporterbyTimestamp calls to the old tellorFlex
    /// @param _queryId queryId of interest
    /// @param _timestamp timestamp you want data for
    function getReporterByTimestamp(bytes32 _queryId, uint256 _timestamp) external view returns(address) {
        return tellorFlex.getReporterByTimestamp(_queryId, _timestamp);
    }

    /// @notice This forwards getTimestampbyQueryIdandIndex calls to the old tellorFlex
    /// @param _queryId queryId of interest
    /// @param _index index you want data for
    function getTimestampbyQueryIdandIndex(bytes32 _queryId, uint256 _index) external view returns(uint256) {
        return tellorFlex.getTimestampbyQueryIdandIndex(_queryId, _index);
    }

    /// @notice This forwards getTimeOfLastNewValue calls to the old tellorFlex
    function getTimeOfLastNewValue() external view returns(uint256) {
        return tellorFlex.getTimeOfLastNewValue();
    }

    /// @notice This forwards isInDispute calls to the old tellorFlex
    /// @param _queryId queryId of interest
    /// @param _timestamp timestamp you want data for
    function isInDispute(bytes32 _queryId, uint256 _timestamp) external view returns(bool) {
        return tellorFlex.isInDispute(_queryId, _timestamp);
    }

    /// @notice This forwards retrieveData calls to the old tellorFlex
    /// @param _queryId being requested
    /// @param _timestamp to retrieve data/value from
    /// @return bytes value for timestamp submitted
    function retrieveData(bytes32 _queryId, uint256 _timestamp) external view returns(bytes memory) {
        return tellorFlex.retrieveData(_queryId, _timestamp);
    }

    /// @notice This returns a big number.  Necessary for upgrading the contract
    function verify() external pure returns (uint256) {
        return 9999;
    }
}


// File: contracts/token-bridge/TokenBridge.sol


pragma solidity 0.8.19;



/// @author Tellor Inc.
/// @title TokenBridge
/// @dev This is the tellor token bridge to move tokens from
/// Ethereum to layer.  No one needs to do this.  The only reason you 
/// move your tokens over is to become a reporter/validator/tipper.  It works by
/// using layer itself as the bridge and then reads the lightclient contract for 
/// bridging back.  There is a long delay in bridging back (enforced by layer) of 12 hours
contract TokenBridge is LayerTransition{
    /*Storage*/
    IBlobstreamO public bridge;
    uint256 public depositId; // counter of how many deposits have been made
    uint256 public depositLimitUpdateTime; // last time the deposit limit was updated
    uint256 public depositLimitRecord; // amount you can deposit per limit period
    BridgeState public bridgeState; // state of the bridge
    uint256 public bridgeStateUpdateTime; // last time the bridge state was updated
    uint256 public withdrawLimitUpdateTime; // last time the withdraw limit was updated
    uint256 public withdrawLimitRecord; // amount you can withdraw per limit period
    uint256 public constant DEPOSIT_LIMIT_DENOMINATOR = 100e18 / 20e18; // 100/depositLimitPercentage
    uint256 public constant MS_PER_SECOND = 1000; // factor to convert milliseconds to seconds
    uint256 public constant PAUSE_PERIOD = 21 days; // time period guardian can pause bridge, only once
    uint256 public constant PAUSE_TRIBUTE_AMOUNT = 10000 ether; // amount of tokens burned to pause bridge
    uint256 public constant TOKEN_DECIMAL_PRECISION_MULTIPLIER = 1e12; // multiplier to convert from loya to 1e18
    uint256 public constant TWELVE_HOUR_CONSTANT = 12 hours; // deposit and withdraw limits update interval
    uint256 public constant WITHDRAW_LIMIT_DENOMINATOR = 100e18 / 5e18; // 100/withdrawLimitPercentage

    mapping(uint256 depositId => DepositDetails) public deposits; // deposit id => deposit details
    mapping(address recipient => uint256 extraAmountToClaim) public tokensToClaim; // recipient => extra amount to claim
    mapping(uint256 withdrawId => bool claimed) public withdrawClaimed; // withdraw id => claimed status

    struct DepositDetails {
        address sender;
        string recipient;
        uint256 amount;
        uint256 tip;
        uint256 blockHeight;
    }

    enum BridgeState {
        NORMAL,
        PAUSED,
        UNPAUSED
    }

    /*Events*/
    event BridgeStateUpdated(BridgeState _newState);
    event ExtraWithdrawClaimed(address _recipient, uint256 _amount);
    event Deposit(uint256 _depositId, address _sender, string _recipient, uint256 _amount, uint256 _tip);
    event Withdraw(uint256 _depositId, string _sender, address _recipient, uint256 _amount);

    // Functions
    /*Functions*/
    /// @notice constructor
    /// @param _token address of tellor token for bridging
    /// @param _blobstream address of BlobstreamO data bridge
    /// @param _tellorFlex address of oracle(tellorFlex) on chain
    constructor(address _token, address _blobstream, address _tellorFlex) LayerTransition(_tellorFlex, _token){
        bridge = IBlobstreamO(_blobstream);
    }

    /// @notice claim extra withdraws that were not fully withdrawn
    /// @param _recipient address of the recipient
    function claimExtraWithdraw(address _recipient) external {
        require(bridgeState != BridgeState.PAUSED, "TokenBridge: bridge is paused");
        uint256 _amountConverted = tokensToClaim[_recipient];
        require(_amountConverted > 0, "amount must be > 0");
        uint256 _withdrawLimit = _refreshWithdrawLimit(_amountConverted);
        require(_withdrawLimit > 0, "TokenBridge: withdraw limit must be > 0");
        if(_withdrawLimit < _amountConverted){
            tokensToClaim[_recipient] = tokensToClaim[_recipient] - _withdrawLimit;
            _amountConverted = _withdrawLimit;
        }
        else{
            tokensToClaim[_recipient] = 0;
        }
        withdrawLimitRecord -= _amountConverted;
        require(token.transfer(_recipient, _amountConverted), "TokenBridge: transfer failed");
        emit ExtraWithdrawClaimed(_recipient, _amountConverted);
    }

    /// @notice deposits tokens from Ethereum to layer
    /// @param _amount total amount of tokens to bridge over
    /// @param _tip amount of tokens to tip the claimDeposit caller on layer
    /// @param _layerRecipient your cosmos address on layer (don't get it wrong!!)
    function depositToLayer(uint256 _amount, uint256 _tip, string memory _layerRecipient) external {
        require(_amount > 0.1 ether, "TokenBridge: amount must be greater than 0.1 tokens");
        require(_amount % TOKEN_DECIMAL_PRECISION_MULTIPLIER == 0, "TokenBridge: amount must be divisible by 1e12");
        require(_amount <= _refreshDepositLimit(_amount), "TokenBridge: amount exceeds deposit limit for time period");
        require(_tip <= _amount, "TokenBridge: tip must be less than or equal to amount");
        if (_tip > 0) {
            require(_tip >= 1e12, "TokenBridge: tip must be greater than or equal to 1 loya");
        }
        require(token.transferFrom(msg.sender, address(this), _amount), "TokenBridge: transferFrom failed");
        depositId++;
        depositLimitRecord -= _amount;
        deposits[depositId] = DepositDetails(msg.sender, _layerRecipient, _amount, _tip, block.number);
        emit Deposit(depositId, msg.sender, _layerRecipient, _amount, _tip);
    }

    /// @notice temporarily pauses the bridge, only once and only by guardian at a great cost
    /// @dev guardian is the only one who can pause the bridge
    function pauseBridge() external {
        require(msg.sender == bridge.guardian(), "TokenBridge: only guardian can pause bridge");
        require(bridgeState == BridgeState.NORMAL, "TokenBridge: can only pause once");
        require(token.transferFrom(msg.sender, address(0xdEaD), PAUSE_TRIBUTE_AMOUNT), "TokenBridge: transfer failed");
        bridgeState = BridgeState.PAUSED;
        bridgeStateUpdateTime = block.timestamp;
        emit BridgeStateUpdated(BridgeState.PAUSED);
    }

    /// @notice unpauses the bridge after the pause period has passed, can be called by anyone
    function unpauseBridge() external {
        require(bridgeState == BridgeState.PAUSED, "TokenBridge: bridge is not paused");
        require(block.timestamp - bridgeStateUpdateTime > PAUSE_PERIOD, "TokenBridge: must wait before unpausing");
        bridgeState = BridgeState.UNPAUSED;
        emit BridgeStateUpdated(BridgeState.UNPAUSED);
    }

    /// @notice This withdraws tokens from layer to mainnet Ethereum
    /// @param _attestData The data being verified
    /// @param _valset array of current validator set
    /// @param _sigs Signatures
    /// @param _depositId depositId from the layer side
    function withdrawFromLayer(
        OracleAttestationData calldata _attestData,
        Validator[] calldata _valset,
        Signature[] calldata _sigs,
        uint256 _depositId
    ) external {
        require(bridgeState != BridgeState.PAUSED, "TokenBridge: bridge is paused");
        require(_attestData.queryId == keccak256(abi.encode("TRBBridge", abi.encode(false, _depositId))), "TokenBridge: invalid queryId");
        require(!withdrawClaimed[_depositId], "TokenBridge: withdraw already claimed");
        require(block.timestamp - (_attestData.report.timestamp / MS_PER_SECOND) > TWELVE_HOUR_CONSTANT, "TokenBridge: premature attestation");
        require(block.timestamp - (_attestData.attestationTimestamp / MS_PER_SECOND) < TWELVE_HOUR_CONSTANT, "TokenBridge: attestation too old");
        bridge.verifyOracleData(_attestData, _valset, _sigs);
        require(_attestData.report.aggregatePower >= bridge.powerThreshold(), "Report aggregate power must be greater than or equal to _minimumPower");
        withdrawClaimed[_depositId] = true;    
        (address _recipient, string memory _layerSender,uint256 _amountLoya,) = abi.decode(_attestData.report.value, (address, string, uint256, uint256));
        uint256 _amountConverted = _amountLoya * TOKEN_DECIMAL_PRECISION_MULTIPLIER; 
        uint256 _withdrawLimit = _refreshWithdrawLimit(_amountConverted);
        if(_withdrawLimit < _amountConverted){
            tokensToClaim[_recipient] = tokensToClaim[_recipient] + (_amountConverted - _withdrawLimit);
            _amountConverted = _withdrawLimit;
        }
        withdrawLimitRecord -= _amountConverted;
        require(token.transfer(_recipient, _amountConverted), "TokenBridge: transfer failed");
        emit Withdraw(_depositId, _layerSender, _recipient, _amountConverted);
    }

    /* View Functions */
    /// @notice returns the amount of tokens that can be deposited in the current 12 hour period
    /// @return amount of tokens that can be deposited
    function depositLimit() external view returns (uint256) {
        if (block.timestamp - depositLimitUpdateTime > TWELVE_HOUR_CONSTANT) {
            return (token.balanceOf(address(this)) + _getMintAmount()) / DEPOSIT_LIMIT_DENOMINATOR;
        }
        else{
            return depositLimitRecord;
        }
    }

    /// @notice returns the withdraw limit
    /// @return amount of tokens that can be withdrawn
    function withdrawLimit() external view returns (uint256) {
        if (block.timestamp - withdrawLimitUpdateTime > TWELVE_HOUR_CONSTANT) {
            return (token.balanceOf(address(this)) + _getMintAmount()) / WITHDRAW_LIMIT_DENOMINATOR;
        }
        else{
            return withdrawLimitRecord;
        }
    }

    /* Internal Functions */
    /// @notice returns the amount of tokens pending to be minted to this contract
    /// @return amount of tokens pending to be minted
    function _getMintAmount() internal view returns (uint256) {
        uint256 _releasedAmount = (146.94 ether *
            (block.timestamp - token.getUintVar(keccak256("_LAST_RELEASE_TIME_DAO")))) /
            86400;
        return _releasedAmount;
    }

    /// @notice refreshes the deposit limit every 12 hours so no one can spam layer with new tokens
    /// @return max amount of tokens that can be deposited
    function _refreshDepositLimit(uint256 _amount) internal returns (uint256) {
        if (block.timestamp - depositLimitUpdateTime > TWELVE_HOUR_CONSTANT) {
            uint256 _tokenBalance = token.balanceOf(address(this));
            if (_tokenBalance < _amount) {
                token.mintToOracle();
                _tokenBalance = token.balanceOf(address(this));
            }
            depositLimitRecord = _tokenBalance / DEPOSIT_LIMIT_DENOMINATOR;
            depositLimitUpdateTime = block.timestamp;
        } 
        return depositLimitRecord;
    }

    /// @notice refreshes the withdraw limit every 12 hours so no one can spam layer with new tokens
    /// @param _amount of tokens to withdraw
    /// @return max amount of tokens that can be withdrawn
    function _refreshWithdrawLimit(uint256 _amount) internal returns (uint256) {
        if (block.timestamp - withdrawLimitUpdateTime > TWELVE_HOUR_CONSTANT) {
            uint256 _tokenBalance = token.balanceOf(address(this));
            if (_tokenBalance < _amount) {
                token.mintToOracle();
                _tokenBalance = token.balanceOf(address(this));
            }
            withdrawLimitRecord = _tokenBalance / WITHDRAW_LIMIT_DENOMINATOR;
            withdrawLimitUpdateTime = block.timestamp;
        } 
        return withdrawLimitRecord;
    }
}