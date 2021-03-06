# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
from unittest import TestCase

from grpc import ServicerContext
from mock import Mock, MagicMock

from qrl.core import logger
from qrl.core.BufferedChain import BufferedChain
from qrl.core.StakeValidatorsTracker import StakeValidatorsTracker
from qrl.core.Transaction import TransferTransaction
from qrl.core.node import SyncState
from qrl.core.p2pfactory import P2PFactory
from qrl.core.qrlnode import QRLNode
from qrl.core.State import State
from qrl.crypto.misc import sha256
from qrl.generated import qrl_pb2
from qrl.services.PublicAPIService import PublicAPIService

logger.initialize_default(force_console_output=True)


class PublicAPITest(TestCase):
    def __init__(self, *args, **kwargs):
        super(PublicAPITest, self).__init__(*args, **kwargs)

    def test_getNodeState(self):
        db_state = Mock(spec=State)
        p2p_factory = Mock(spec=P2PFactory)
        p2p_factory.sync_state = SyncState()
        p2p_factory.connections = 23
        p2p_factory.stake = False

        buffered_chain = Mock(spec=BufferedChain)
        buffered_chain.height = MagicMock(return_value=0)

        qrlnode = QRLNode(db_state)
        qrlnode.set_p2pfactory(p2p_factory)
        qrlnode.set_chain(buffered_chain)

        service = PublicAPIService(qrlnode)
        node_state = service.GetNodeState(request=qrl_pb2.GetNodeStateReq, context=None)

        # self.assertEqual(__version__, node_state.info.version)  # FIXME
        self.assertEqual(qrl_pb2.NodeInfo.UNSYNCED, node_state.info.state)
        self.assertEqual(23, node_state.info.num_connections)
        # self.assertEqual("testnet", node_state.info.network_id)  # FIXME

    def test_getStats(self):
        db_state = Mock(spec=State)
        db_state.stake_validators_tracker = StakeValidatorsTracker()
        db_state.total_coin_supply = MagicMock(return_value=1000)

        p2p_factory = Mock(spec=P2PFactory)
        p2p_factory.sync_state = SyncState()
        p2p_factory.connections = 23
        p2p_factory.stake = False

        buffered_chain = Mock(spec=BufferedChain)
        buffered_chain.height = MagicMock(return_value=0)
        buffered_chain.blockchain = []
        buffered_chain.get_block = MagicMock(return_value=None)
        buffered_chain.state = db_state

        qrlnode = QRLNode(db_state)
        qrlnode.set_p2pfactory(p2p_factory)
        qrlnode.set_chain(buffered_chain)

        service = PublicAPIService(qrlnode)
        stats = service.GetStats(request=qrl_pb2.GetStatsReq, context=None)

        # self.assertEqual(__version__, stats.node_info.version)  # FIXME
        self.assertEqual(qrl_pb2.NodeInfo.UNSYNCED, stats.node_info.state)
        self.assertEqual(23, stats.node_info.num_connections)
        # self.assertEqual("testnet", stats.node_info.network_id)  # FIXME

        self.assertEqual(0, stats.epoch)
        self.assertEqual(0, stats.uptime_network)

        self.assertEqual(0, stats.stakers_count)

        self.assertEqual(0, stats.block_last_reward)
        self.assertEqual(0, stats.block_time_mean)
        self.assertEqual(0, stats.block_time_sd)

        self.assertEqual(105000000, stats.coins_total_supply)
        self.assertEqual(1000, stats.coins_emitted)
        self.assertEqual(0, stats.coins_atstake)

        print(stats)

    def test_getKnownPeers(self):
        db_state = Mock(spec=State)
        p2p_factory = Mock(spec=P2PFactory)
        p2p_factory.sync_state = SyncState()
        p2p_factory.connections = 23
        p2p_factory.stake = False

        buffered_chain = Mock(spec=BufferedChain)
        buffered_chain.height = MagicMock(return_value=0)

        qrlnode = QRLNode(db_state)
        qrlnode.set_p2pfactory(p2p_factory)
        qrlnode.set_chain(buffered_chain)
        qrlnode._peer_addresses = ['127.0.0.1', '192.168.1.1']

        service = PublicAPIService(qrlnode)
        response = service.GetKnownPeers(request=qrl_pb2.GetKnownPeersReq, context=None)

        self.assertEqual(2, len(response.known_peers))
        self.assertEqual('127.0.0.1', response.known_peers[0].ip)
        self.assertEqual('192.168.1.1', response.known_peers[1].ip)

        print(response)

    def test_getAddressState(self):
        db_state = Mock(spec=State)
        db_state.get_address = MagicMock(return_value=(25, 10, [sha256(b'a'), sha256(b'b')]))
        db_state.get_address_tx_hashes = MagicMock(return_value=[sha256(b'0'), sha256(b'1')])

        p2p_factory = Mock(spec=P2PFactory)
        buffered_chain = Mock(spec=BufferedChain)

        qrlnode = QRLNode(db_state)
        qrlnode.set_p2pfactory(p2p_factory)
        qrlnode.set_chain(buffered_chain)
        qrlnode._peer_addresses = ['127.0.0.1', '192.168.1.1']

        service = PublicAPIService(qrlnode)

        context = Mock(spec=ServicerContext)
        request = qrl_pb2.GetAddressStateReq()
        response = service.GetAddressState(request=request, context=context)
        context.set_code.assert_called()
        context.set_details.assert_called()

        context = Mock(spec=ServicerContext)
        request = qrl_pb2.GetAddressStateReq()
        request.address = b'Qa02d909723512ecd1606c96f52f5a4121946f068986e612a57c75353952ab3624ddd0bd6'
        response = service.GetAddressState(request=request, context=context)
        context.set_code.assert_not_called()
        self.assertEqual(b'Qa02d909723512ecd1606c96f52f5a4121946f068986e612a57c75353952ab3624ddd0bd6',
                         response.state.address)
        self.assertEqual(25, response.state.nonce)
        self.assertEqual(10, response.state.balance)
        self.assertEqual([sha256(b'a'), sha256(b'b')], response.state.pubhashes)
        self.assertEqual([sha256(b'0'), sha256(b'1')], response.state.transaction_hashes)

    def test_getObject(self):
        SOME_ADDR1 = b'Qa02d909723512ecd1606c96f52f5a4121946f068986e612a57c75353952ab3624ddd0bd6'
        SOME_ADDR2 = b'Qa02d909723512ecd1606c96f52f5a4121946f068986e612a57c75353952ab3624ddd0bd7'

        db_state = Mock(spec=State)

        p2p_factory = Mock(spec=P2PFactory)
        buffered_chain = Mock(spec=BufferedChain)
        buffered_chain.tx_pool = Mock()
        buffered_chain.tx_pool.transaction_pool = []

        qrlnode = QRLNode(db_state)
        qrlnode.set_p2pfactory(p2p_factory)
        qrlnode.set_chain(buffered_chain)
        qrlnode._peer_addresses = ['127.0.0.1', '192.168.1.1']

        service = PublicAPIService(qrlnode)

        context = Mock(spec=ServicerContext)
        request = qrl_pb2.GetObjectReq()
        response = service.GetObject(request=request, context=context)
        context.set_code.assert_not_called()
        context.set_details.assert_not_called()
        self.assertFalse(response.found)

        # Find an address
        db_state.get_address = MagicMock(return_value=(25, 10, [sha256(b'a'), sha256(b'b')]))
        db_state.get_address_tx_hashes = MagicMock(return_value=[sha256(b'0'), sha256(b'1')])

        context = Mock(spec=ServicerContext)
        request = qrl_pb2.GetObjectReq()
        request.query = SOME_ADDR1
        response = service.GetObject(request=request, context=context)
        context.set_code.assert_not_called()
        self.assertTrue(response.found)
        self.assertIsNotNone(response.address_state)
        self.assertEqual(SOME_ADDR1,
                         response.address_state.address)
        self.assertEqual(25, response.address_state.nonce)
        self.assertEqual(10, response.address_state.balance)
        self.assertEqual([sha256(b'a'), sha256(b'b')], response.address_state.pubhashes)
        self.assertEqual([sha256(b'0'), sha256(b'1')], response.address_state.transaction_hashes)

        # Find a transaction
        db_state.address_used = MagicMock(return_value=False)
        tx1 = TransferTransaction.create(addr_from=SOME_ADDR1,
                                         addr_to=SOME_ADDR2,
                                         amount=125,
                                         fee=19,
                                         xmss_pk=sha256(b'pk'),
                                         xmss_ots_index=13)

        buffered_chain.tx_pool.transaction_pool = [tx1]

        context = Mock(spec=ServicerContext)
        request = qrl_pb2.GetObjectReq()
        request.query = tx1.txhash
        response = service.GetObject(request=request, context=context)
        context.set_code.assert_not_called()
        self.assertTrue(response.found)
        self.assertIsNotNone(response.transaction)
        self.assertEqual(qrl_pb2.Transaction.TRANSFER, response.transaction.type)
        self.assertEqual(SOME_ADDR1, response.transaction.addr_from)
        self.assertEqual(sha256(b'pk'), response.transaction.public_key)
        self.assertEqual(tx1.txhash, response.transaction.transaction_hash)
        self.assertEqual(13, response.transaction.ots_key)
        self.assertEqual(b'', response.transaction.signature)

        self.assertEqual(SOME_ADDR2, response.transaction.transfer.addr_to)
        self.assertEqual(125, response.transaction.transfer.amount)
        self.assertEqual(19, response.transaction.transfer.fee)

        # Find a block
