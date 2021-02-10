import sys
import base64

import concurrent.futures as conc
from options import get_options

from minecraft import authentication
from minecraft.networking.connection import Connection
from minecraft.networking.packets import Packet, clientbound, serverbound
from minecraft import PROTOCOL_VERSION_INDICES, KNOWN_MINECRAFT_VERSIONS

def add_vec(v1, v2):
	if len(v1) == len(v2):
		vres = tuple(v1)
		for i in range(len(vres)):
			vres[i] = vres[i] + v2
		return vres
	raise ValueError("Attempt to add unequal dimensional vectors")

def main():
	# Get commandline options
	options = get_options()

	# Establish connection with the server
	connection = Connection(options.address, options.port, username=options.username)	
	print("[DEBUG] Protocol Version: %s" % connection.context.protocol_version)

	def respawn():
		print("Respawning...")
		packet = serverbound.play.ClientStatusPacket()
		packet.action_id = serverbound.play.ClientStatusPacket.RESPAWN
		connection.write_packet(packet)

	player_id = None
	player_eid_to_uuid = {}
	players = {}

	@connection.listener(clientbound.play.JoinGamePacket)
	def handle_join_game(join_game_packet):
		player_id = join_game_packet.entity_id
		print('Connected (id: %s)' % player_id)

	@connection.listener(clientbound.play.PlayerListItemPacket)
	def handle_player_list(player_list_packet):
		if player_list_packet.action_type == clientbound.play.PlayerListItemPacket.AddPlayerAction:
			for action in player_list_packet.actions:
				players[action.uuid] = {"name": action.name}
				print("AddPlayer: %s (uuid: %s)" % (action.name, action.uuid))
		if player_list_packet.action_type == clientbound.play.PlayerListItemPacket.RemovePlayerAction:
			for action in player_list_packet.actions:
				players.pop(action.uuid)
				print("RemovePlayer: %s (uuid: %s)" % (action.name, action.uuid))

	@connection.listener(clientbound.play.SpawnPlayerPacket)
	def handle_spawn_player(player_spawn_packet):
		if player_spawn_packet.player_UUID in players:
			player_eid_to_uuid[player_spawn_packet.entity_id] = player_spawn_packet.player_UUID
			players[player_spawn_packet.player_UUID]["entity_id"] = player_spawn_packet.entity_id
			players[player_spawn_packet.player_UUID]["position"] = player_spawn_packet.position

	@connection.listener(clientbound.play.CombatEventPacket)
	def handle_combat_event(combat_event_packet):
		if combat_event_packet.event.id == clientbound.play.CombatEventPacket.EntityDeadEvent.id:
			if combat_event_packet.event.player_id == player_id:
				print("%s DIED!" % combat_event_packet.event.player_id)
				#respawn()

	@connection.listener(clientbound.play.PlayerPositionAndLookPacket)
	def handle_player_pos(position_and_look_packet):
		print("Position: %s %s %s" % (position_and_look_packet.x, position_and_look_packet.y, position_and_look_packet.z))

	@connection.listener(clientbound.play.UpdateHealthPacket)
	def handle_update_health(update_health_packet):
		if handle_update_health.counter == 0:
			print("[%s] Health: %s" % (handle_update_health.counter, update_health_packet.health))
		handle_update_health.counter = 0 if handle_update_health.counter == 7 \
									else handle_update_health.counter + 1
		if update_health_packet.health == 0: respawn()
	handle_update_health.counter = 0

	@connection.listener(clientbound.play.EntityPositionDeltaPacket)
	def handle_entity_position(position_packet):
		if position_packet.entity_id in player_eid_to_uuid:
			uuid = player_eid_to_uuid[position_packet.entity_id]
			players[uuid]["position"] = players[uuid]["position"] + position_packet.delta_position

	connection.connect()

	while True:
		try:
			text = input()
			if text == "/respawn":
				respawn()
			elif text == "list-players":
				for uuid in players:
					print("%s (uuid: %s)" % (players[uuid], uuid))
		except KeyboardInterrupt:
			print("Disconnecting")
			sys.exit()

if __name__ == "__main__":
	main()

