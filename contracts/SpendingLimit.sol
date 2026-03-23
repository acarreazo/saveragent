// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * SaverAgent - SpendingLimit.sol
 * Deploy en Celo Sepolia Testnet (chainId: 11142220)
 *
 * Permite al usuario autorizar al agente a gastar
 * hasta un limite de USDC por periodo de tiempo.
 * El agente NUNCA puede exceder el limite autorizado.
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract SpendingLimit {

    // ── Eventos ───────────────────────────────────────────────────
    event LimitSet(
        address indexed user,
        address indexed agent,
        uint256 limitPerPeriod,
        uint256 periodSeconds
    );
    event TransferExecuted(
        address indexed user,
        address indexed to,
        uint256 amount,
        string  goalName,
        uint256 timestamp
    );
    event LimitRevoked(address indexed user, address indexed agent);

    // ── Estructuras ───────────────────────────────────────────────
    struct Permission {
        uint256 limitPerPeriod;
        uint256 periodSeconds;
        uint256 spentThisPeriod;
        uint256 periodStart;
        bool    active;
    }

    struct TransferRecord {
        address to;
        uint256 amount;
        string  goalName;
        uint256 timestamp;
    }

    // ── Estado ────────────────────────────────────────────────────
    // user => agent => Permission
    mapping(address => mapping(address => Permission)) public permissions;
    mapping(address => TransferRecord[]) public transferHistory;

    // USDC en Celo Sepolia
    address public constant TOKEN_ADDRESS =
        0x01C5C0122039549AD1493B8220cABEdD739BC44E;

    IERC20 public immutable token;

    constructor() {
        token = IERC20(TOKEN_ADDRESS);
    }

    // ── Funciones del usuario ─────────────────────────────────────

    /**
     * Autoriza al agente a gastar hasta X tokens por periodo.
     * Ejemplo: setLimit(agentAddr, 1000000, 86400)
     *   = agente puede gastar hasta 1 USDC por dia (6 decimales)
     */
    function setLimit(
        address agent,
        uint256 limitPerPeriod,
        uint256 periodSeconds
    ) external {
        require(agent != address(0), "Agent invalido");
        require(limitPerPeriod > 0,  "Limite debe ser > 0");
        require(periodSeconds  > 0,  "Periodo debe ser > 0");

        permissions[msg.sender][agent] = Permission({
            limitPerPeriod:  limitPerPeriod,
            periodSeconds:   periodSeconds,
            spentThisPeriod: 0,
            periodStart:     block.timestamp,
            active:          true
        });

        emit LimitSet(msg.sender, agent, limitPerPeriod, periodSeconds);
    }

    function revokeLimit(address agent) external {
        require(permissions[msg.sender][agent].active, "No hay permiso activo");
        permissions[msg.sender][agent].active = false;
        emit LimitRevoked(msg.sender, agent);
    }

    // ── Funciones del agente ──────────────────────────────────────

    function executeTransfer(
        address user,
        address to,
        uint256 amount,
        string calldata goalName
    ) external {
        Permission storage perm = permissions[user][msg.sender];

        require(perm.active, "Permiso no activo");
        require(amount > 0,  "Monto debe ser > 0");

        // Resetear periodo si expiro
        if (block.timestamp >= perm.periodStart + perm.periodSeconds) {
            perm.spentThisPeriod = 0;
            perm.periodStart     = block.timestamp;
        }

        require(
            perm.spentThisPeriod + amount <= perm.limitPerPeriod,
            "Excede el limite autorizado"
        );

        perm.spentThisPeriod += amount;

        bool ok = token.transferFrom(user, to, amount);
        require(ok, "Transferencia fallida");

        transferHistory[user].push(TransferRecord({
            to:        to,
            amount:    amount,
            goalName:  goalName,
            timestamp: block.timestamp
        }));

        emit TransferExecuted(user, to, amount, goalName, block.timestamp);
    }

    // ── Consultas ─────────────────────────────────────────────────

    function getAvailableBalance(
        address user,
        address agent
    ) external view returns (uint256) {
        Permission storage perm = permissions[user][agent];
        if (!perm.active) return 0;
        if (block.timestamp >= perm.periodStart + perm.periodSeconds)
            return perm.limitPerPeriod;
        if (perm.spentThisPeriod >= perm.limitPerPeriod) return 0;
        return perm.limitPerPeriod - perm.spentThisPeriod;
    }

    function getHistory(
        address user
    ) external view returns (TransferRecord[] memory) {
        return transferHistory[user];
    }

    function getPermission(
        address user,
        address agent
    ) external view returns (
        uint256 limitPerPeriod,
        uint256 spentThisPeriod,
        uint256 availableNow,
        bool    active
    ) {
        Permission storage perm = permissions[user][agent];
        uint256 available = 0;
        if (perm.active) {
            if (block.timestamp >= perm.periodStart + perm.periodSeconds)
                available = perm.limitPerPeriod;
            else
                available = perm.limitPerPeriod > perm.spentThisPeriod
                    ? perm.limitPerPeriod - perm.spentThisPeriod : 0;
        }
        return (perm.limitPerPeriod, perm.spentThisPeriod, available, perm.active);
    }
}
