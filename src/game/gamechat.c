#include <ultra64.h>
#include <stdio.h>
#include <string.h>
#include "constants.h"
#include "game/gamechat.h"
#include "game/game_1531a0.h"
#include "game/hudmsg.h"
#include "game/menu.h"
#include "game/playermgr.h"
#include "input.h"
#include "net/net.h"
#include "bss.h"
#include "data.h"
#include "types.h"

#define GAMECHAT_MAXLEN 120
#define GAMECHAT_MAX_MESSAGES 8

static char g_GameChatDraft[GAMECHAT_MAXLEN + 1];
static char g_GameChatPending[GAMECHAT_MAX_MESSAGES][192];
static s32 g_GameChatPendingHead = 0;
static s32 g_GameChatPendingTail = 0;
static s32 g_GameChatPendingCount = 0;

static const char *gameChatGetLocalSenderName(void)
{
	if (g_NetMode && g_NetLocalClient && g_NetLocalClient->settings.name[0] != '\0') {
		return g_NetLocalClient->settings.name;
	}

	if (g_MpPlayerNum >= 0 && g_MpPlayerNum < MAX_PLAYERS) {
		static char namebuf[MAX_PLAYERNAME + 1];
		s32 i;

		for (i = 0; i < MAX_PLAYERNAME && g_PlayerConfigsArray[g_MpPlayerNum].base.name[i] != '\0'; i++) {
			if (g_PlayerConfigsArray[g_MpPlayerNum].base.name[i] == '\n') {
				break;
			}

			namebuf[i] = g_PlayerConfigsArray[g_MpPlayerNum].base.name[i];
		}

		namebuf[i] = '\0';

		if (namebuf[0] != '\0') {
			return namebuf;
		}
	}

	return "Player";
}

static void gameChatDisplayMessage(const char *text)
{
	char buffer[192];
	struct fontchar *font1 = g_CharsHandelGothicSm;
	struct font *font2 = g_FontHandelGothicSm;

	if (text == NULL || text[0] == '\0') {
		return;
	}

	snprintf(buffer, sizeof(buffer), "%s", text);
	buffer[sizeof(buffer) - 1] = '\0';

	hudmsgCreateFromArgs(
		buffer,
		HUDMSGTYPE_DEFAULT,
		0,
		1,
		0,
		&font1,
		&font2,
		0x00ff0000,
		0x000000a0,
		HUDMSGALIGN_LEFT,
		16,
		HUDMSGALIGN_BOTTOM,
		12,
		180,
		HUDMSGFLAG_ALLOWDUPES | HUDMSGFLAG_NOCHANNEL);
}

void gameChatShowMessage(const char *text)
{
	if (text == NULL || text[0] == '\0') {
		return;
	}

	snprintf(g_GameChatPending[g_GameChatPendingTail], sizeof(g_GameChatPending[g_GameChatPendingTail]), "%s", text);
	g_GameChatPending[g_GameChatPendingTail][sizeof(g_GameChatPending[g_GameChatPendingTail]) - 1] = '\0';
	g_GameChatPendingTail = (g_GameChatPendingTail + 1) % GAMECHAT_MAX_MESSAGES;

	if (g_GameChatPendingCount < GAMECHAT_MAX_MESSAGES) {
		g_GameChatPendingCount++;
	} else {
		g_GameChatPendingHead = (g_GameChatPendingHead + 1) % GAMECHAT_MAX_MESSAGES;
	}
}

void gameChatTick(void)
{
	if (g_GameChatPendingCount <= 0) {
		return;
	}

	if (g_MainIsEndscreen || g_Vars.currentplayer == NULL || g_Vars.currentplayer->isremote) {
		return;
	}

	while (g_GameChatPendingCount > 0) {
		gameChatDisplayMessage(g_GameChatPending[g_GameChatPendingHead]);
		g_GameChatPendingHead = (g_GameChatPendingHead + 1) % GAMECHAT_MAX_MESSAGES;
		g_GameChatPendingCount--;
	}
}

static char *gameChatMenuTitle(struct menudialogdef *dialogdef)
{
	return "Match Chat";
}

static MenuItemHandlerResult gameChatKeyboardHandler(s32 operation, struct menuitem *item, union handlerdata *data)
{
	char *text = data->keyboard.string;
	s32 i;

	switch (operation) {
	case MENUOP_GETTEXT:
		for (i = 0; i < (s32)ARRAYCOUNT(g_GameChatDraft); i++) {
			text[i] = g_GameChatDraft[i];
		}
		break;
	case MENUOP_SETTEXT:
		for (i = 0; i < (s32)ARRAYCOUNT(g_GameChatDraft); i++) {
			g_GameChatDraft[i] = text[i];
		}
		break;
	case MENUOP_SET:
		if (g_GameChatDraft[0] != '\0') {
			if (g_NetMode && g_NetLocalClient) {
				if (g_NetMode == NETMODE_SERVER) {
					char buffer[192];

					snprintf(buffer, sizeof(buffer), "%s: %s", gameChatGetLocalSenderName(), g_GameChatDraft);
					buffer[sizeof(buffer) - 1] = '\0';
					gameChatShowMessage(buffer);
				}

				netChat(NULL, g_GameChatDraft);
			} else {
				char buffer[192];

				snprintf(buffer, sizeof(buffer), "%s: %s", gameChatGetLocalSenderName(), g_GameChatDraft);
				buffer[sizeof(buffer) - 1] = '\0';
				gameChatShowMessage(buffer);
			}

			g_GameChatDraft[0] = '\0';
		}
		break;
	}

	return 0;
}

static struct menuitem g_GameChatMenuItems[] = {
	{
		MENUITEMTYPE_LABEL,
		0,
		MENUITEMFLAG_LESSLEFTPADDING | MENUITEMFLAG_LITERAL_TEXT,
		(uintptr_t) "Enter chat message:",
		0,
		NULL,
	},
	{
		MENUITEMTYPE_KEYBOARD,
		GAMECHAT_MAXLEN,
		0,
		0,
		1,
		gameChatKeyboardHandler,
	},
	{ MENUITEMTYPE_END },
};

static struct menudialogdef g_GameChatMenuDialog = {
	MENUDIALOGTYPE_DEFAULT,
	(uintptr_t) &gameChatMenuTitle,
	g_GameChatMenuItems,
	NULL,
	MENUDIALOGFLAG_DISABLEBANNER,
	NULL,
};

void gameChatOpen(void)
{
	if (g_MainIsEndscreen) {
		return;
	}

	if (g_Vars.currentplayer == NULL || g_Vars.currentplayer->isremote) {
		return;
	}

	if (g_Vars.currentplayer->pausemode != PAUSEMODE_UNPAUSED) {
		return;
	}

	if (currentPlayerIsMenuOpenInSoloOrMp()) {
		return;
	}

	menuPushRootDialog(&g_GameChatMenuDialog, g_Vars.mplayerisrunning ? MENUROOT_MPPAUSE : MENUROOT_MAINMENU);
	g_MenuKeyboardPlayer = g_MpPlayerNum;
	inputClearLastTextChar();
	inputStartTextInput();
}
