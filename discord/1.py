import discord, os, asyncio, datetime, io, random, matplotlib, json
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import sympy as sp, matplotlib.pyplot as plt, google.genai as genai, google.genai.types as types

class setup:
    def __init__(self):
        self.settings()
    def settings(self):
        matplotlib.use('Agg')
        matplotlib.rcParams['mathtext.fontset'] = 'stix'
        token = "MTQ2NzA5NjM3OTE3MTI3NDg2NQ.G1Y0iH.Z6M7F6Kzao68MRjpjGhhvgTxmTPN5UxmmHZ3P4"
        JST = datetime.timezone(datetime.timedelta(hours=9))
        intents = discord.Intents.default()
        intents.message_content = True
        client = commands.Bot(command_prefix="!", intents=intents)
        ADMIN_ROLE_ID = 1554309276200337418
        TICKET_CATEGORY_ID = 1554363808707776602
        ai = genai.Client(api_key="AIzaSyAsUW_5hGM7TlGNAZmCmZGHO0t-uxy6lJ8")
        return token, JST, client, ADMIN_ROLE_ID, TICKET_CATEGORY_ID, ai
    def dict(self):
        user_statuses = {}
        STATUS_CONFIG = {
            "available": {"label": "対応可能", "emoji": "🟢", "embed_text": "🟢 **対応可能**"},
            "away": {"label": "離席中", "emoji": "🟡", "embed_text": "🟡 **離席中**"},
            "busy": {"label": "対応不可", "emoji": "🔴", "embed_text": "🔴 **対応不可**"},
        }
        QUIZ_POOL = {
            "easy": [
                ("x**2", "x", 0, 3),
                ("x**3", "x", 0, 2),
                ("2*x + 1", "x", 1, 3),
                ("x**2 + x", "x", 0, 2),
                ("x**2 + 3x + 6", "x", 0, 3),
                ("x**2 + x + 6", "x", 0, 2),
            ],
            "normal": [
                ("sin(x)", "x", 0, sp.pi),
                ("cos(x)", "x", 0, sp.pi / 2),
                ("exp(x)", "x", 0, 1),
                ("x * cos(x)", "x", 0, sp.pi / 2),
            ],
            "hard": [
                ("x * exp(x**2)", "x", 0, 1),
                ("log(x)", "x", 1, sp.E),
                ("1 / (x**2 + 1)", "x", 0, 1),
                ("x**2 * exp(x)", "x", 0, 1),
            ]
        }
        return user_statuses, STATUS_CONFIG, QUIZ_POOL

setup = setup()
token, JST, client, ADMIN_ROLE_ID, TICKET_CATEGORY_ID, ai = setup.settings()
user_statuses, STATUS_CONFIG, QUIZ_POOL = setup.dict()

class Groups:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    def create_group(self):
        self.group = client.create_group(name=self.name, description=self.description)
        return self.group

set = Groups(name="setup", description="管理者専用のコマンドです。").create_group()

# チケットを閉じる（削除する）ボタンの定義
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # タイムアウトなし
        
    @discord.ui.button(
        label="チケットを閉じる", style=discord.ButtonStyle.danger, emoji="🔒"
    )
    async def close(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("このチケットチャンネルを5秒後に削除します...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# 問い合わせ内容を入力するモーダル
class TicketModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="サポートチケットの作成")
        self.add_item(discord.ui.InputText(label="件名", placeholder="例: ファイルのダウンロードができません", max_length=100))
        self.add_item(discord.ui.InputText(label="お問い合わせ内容", style=discord.InputTextStyle.long, placeholder="詳細をご記入ください...",max_length=1000))

    # 送信ボタンが押された時の処理（ここを書き換えます）
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # チャンネル作成処理中のタイムアウト防止
        guild = interaction.guild
        title = self.children[0].value
        description = self.children[1].value
        
        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)

        if not category or not admin_role:
            await interaction.followup.send("設定エラー: カテゴリまたは管理者ロールが見つかりません。", ephemeral=True)
            return

        # 1. チャンネルのアクセス権限（Overwrites）を設定
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        }

        # 2. カテゴリ内に非公開のテキストチャンネルを作成
        # チャンネル名例: ticket-ユーザー名
        channel_name = f"ticket-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        # 3. 作成した専用チャンネルに送信する埋め込み（Embed）を作成
        embed = discord.Embed(title=f"🎫 お問い合わせ: {title}", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="申請者", value=interaction.user.mention, inline=True)
        embed.add_field(name="内容", value=description, inline=False)
        embed.set_footer(text="対応が完了したら「チケットを閉じる」を押してください。")

        # 4. 作成したチャンネルにメッセージと「閉じるボタン」を送信
        await ticket_channel.send(content=f"{interaction.user.mention} {admin_role.mention}\nサポートチケットが作成されました。", embed=embed,view=CloseButton())

        # 5. 本人への最終完了通知（作成されたチャンネルへのリンク付き）
        await interaction.followup.send(f"専用チケットチャンネルを作成しました: {ticket_channel.mention}", ephemeral=True)

# 3. 問い合わせチャンネルに設置する「チケット作成ボタン」
class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Bot再起動後もボタンを有効化するため無期限に設定

    @discord.ui.button(label="お問い合わせを作成", style=discord.ButtonStyle.primary, emoji="📩", custom_id="create_ticket_button")
    async def create_ticket_click(self, button: discord.ui.Button, interaction: discord.Interaction):
        # ボタンを押したらModal（フォーム）を表示
        await interaction.response.send_modal(TicketModal())

# 4. パネル設置用コマンド（管理者用）
@set.command(name="ticket", description="問い合わせパネルをこのチャンネルに設置します")
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx: discord.ApplicationContext):
    embed = discord.Embed(title="📩 お問い合わせパネル", description="下の「お問い合わせを作成」ボタンを押すと、専用のサポートチケットを発行できます。\n個別の非公開チャンネルが作成されますので、そちらでご用件をお伝えください。", color=discord.Color.blue())
    # ボタン付きでメッセージを送信
    await ctx.respond("パネルを設置しました。", ephemeral=True)
    await ctx.channel.send(embed=embed, view=CreateTicketView())
                                           
def create_status_embed() -> discord.Embed:
    """現在の全体対応状況をまとめた Embed を作成する関数"""
    embed = discord.Embed(title="📋 メンバー対応状況", description="下のボタンを押して、あなたの対応状況を切り替えてください。", color=discord.Color.blue())
    if not user_statuses:
        embed.add_field(name="現在の状況", value="登録されているステータスはありません。", inline=False)
    else:
        status_lines = []
        for user_id, info in user_statuses.items():
            status_text = STATUS_CONFIG.get(info["status"], {}).get("embed_text", info["status"])
            status_lines.append(f"• **{info['name']}**: {status_text}")    
        embed.add_field(name="現在の状況", value="\n".join(status_lines), inline=False)
    return embed

class StatusView(discord.ui.View):
    """対応状況変更用のボタン付き View"""
    def __init__(self):
        super().__init__(timeout=None)  # 永続化（タイムアウトなし）にする場合
    async def update_user_status(self, interaction: discord.Interaction, status_key: str):
        """ステータスを更新し、メッセージを再描画する処理"""
        user = interaction.user
        display_name = user.display_name

        # ステータス辞書を更新
        user_statuses[user.id] = {"name": display_name, "status": status_key}

        # 新しいEmbedを作成してメッセージを更新
        new_embed = create_status_embed()
        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="対応可能", style=discord.ButtonStyle.green, emoji="🟢", custom_id="status_available")
    async def available_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.update_user_status(interaction, "available")
        
    @discord.ui.button(label="離席中", style=discord.ButtonStyle.secondary, emoji="🟡", custom_id="status_away")
    async def away_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.update_user_status(interaction, "away")

    @discord.ui.button(label="対応不可", style=discord.ButtonStyle.danger, emoji="🔴", custom_id="status_busy")
    async def busy_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.update_user_status(interaction, "busy")

@set.command(name="status", description="対応状況パネルを設置します（管理者向け）")
@commands.has_permissions(administrator=True)
async def setup_status(ctx: discord.ApplicationContext):
    embed = create_status_embed()
    view = StatusView()
    await ctx.respond("対応状況パネルを設置しました！", ephemeral=True)
    await ctx.channel.send(embed=embed, view=view)
    
def generate_integral_image_sync(f_str, var_str, lower, upper):
    x = sp.Symbol(var_str)
    f = sp.sympify(f_str)

    # 積分計算
    result = sp.integrate(f, (x, lower, upper))
    
    # SymPyでLaTeX文字列を生成
    latex_code = sp.latex(sp.Integral(f, (x, lower, upper)))
    
    # Matplotlibが対応していない '\limits' を除去
    latex_code = latex_code.replace(r'\limits', '')
    latex_string = f"${latex_code}$"

    # Matplotlib 描画設定
    fig, ax = plt.subplots(figsize=(4.5, 1.5), facecolor='#313338')
    ax.axis('off')
    ax.text(0.5, 0.5, latex_string, fontsize=22, ha='center', va='center', color='white')
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)  
    buf.seek(0)
    plt.close(fig)
    return buf, result

class AnswerModal(discord.ui.Modal):
    def __init__(self, correct_answer, parent_view: View):
        super().__init__(title="積分の答えを入力")
        self.correct_answer = correct_answer
        self.parent_view = parent_view
        self.answer_input = discord.ui.InputText(
            label="計算結果を入力してください（分数・e・pi対応）",
            placeholder="例: 9, 15/2, exp(1)-1, pi/4 など",
            required=True
        )
        self.add_item(self.answer_input)

    async def callback(self, interaction: discord.Interaction):
        if getattr(self.parent_view, "answered", False):
            await interaction.response.send_message("この問題は既に解答されています。", ephemeral=True)
            return
        self.parent_view.answered = True
        user_answer_str = self.answer_input.value.strip()
        try:
            # 入力文字列をSymPy数式として評価
            user_ans = sp.sympify(user_answer_str)
            correct_ans = self.correct_answer

            for child in self.parent_view.children:
                child.disabled = True

            # 差分が0（数学的同値）か判定
            if sp.simplify(user_ans - correct_ans) == 0:
                embed = discord.Embed(title="🎉 正解!", description=f"{interaction.user.mention} さん、正解です！\n答え: `{sp.pretty(correct_ans)}`",color=discord.Color.green())
            else:
                embed = discord.Embed(
                    title="❌ 不正解...",
                    description=f"{interaction.user.mention} さん、残念ながら不正解です。\n**正解:** `{correct_ans}`",
                    color=discord.Color.red()
                )
            await interaction.response.edit_message(embed=embed, view=self.parent_view)

        except Exception:
            for child in self.parent_view.children:
                child.disabled = True
            embed = discord.Embed(
                title="⚠️ エラー",
                description="入力された数式・数値の形式を解析できませんでした。",
                color=discord.Color.orange()
            )
            await interaction.response.edit_message(embed=embed, view=self.parent_view)

# クイズ出題後の「解答する」ボタンを持つView
class IntegralStartView(View):
    def __init__(self, correct_answer):
        super().__init__(timeout=120)
        self.correct_answer = correct_answer
        self.answered = False

    @discord.ui.button(label="解答する", style=discord.ButtonStyle.primary, emoji="✍")
    async def answer_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.answered:
            await interaction.response.send_message("この問題は既に終了しています。", ephemeral=True)
            return
        modal = AnswerModal(self.correct_answer, parent_view=self)
        await interaction.response.send_modal(modal)

# 難易度選択ボタンを表示するView
class DifficultySelectView(View):
    def __init__(self):
        super().__init__(timeout=60)

    async def start_quiz_by_difficulty(self, interaction: discord.Interaction, difficulty_key: str, diff_label: str):
        # 1. インタラクションの処理を開始（ローディング状態にする）
        await interaction.response.defer()

        # 難易度に応じたプールから選択
        f_str, var_str, lower, upper = random.choice(QUIZ_POOL[difficulty_key])

        try:
            # 別スレッドで画像と正解を生成
            img_buf, correct_ans = await asyncio.to_thread(generate_integral_image_sync, f_str, var_str, lower, upper)

            filename = "integral.png"
            file = discord.File(fp=img_buf, filename=filename)

            embed = discord.Embed(title=f"📐 積分計算クイズ 【難易度: {diff_label}】", description="以下の定積分を計算してください。下の「解答する」ボタンを押して答えを入力できます。", color=discord.Color.blurple())
            embed.set_image(url=f"attachment://{filename}")
            view = IntegralStartView(correct_ans)

            # 元の「難易度選択メッセージ」をクイズ画面に上書き更新
            await interaction.edit_original_response(content=None, embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] 積分画像生成エラー: {e}")
            await interaction.followup.send("⚠️ 画像の生成中にエラーが発生しました。", ephemeral=True)

    @discord.ui.button(label="かんたん", style=discord.ButtonStyle.success, emoji="🟢")
    async def easy_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.start_quiz_by_difficulty(interaction, "easy", "かんたん")

    @discord.ui.button(label="ふつう", style=discord.ButtonStyle.primary, emoji="🟡")
    async def normal_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.start_quiz_by_difficulty(interaction, "normal", "ふつう")

    @discord.ui.button(label="むずかしい", style=discord.ButtonStyle.danger, emoji="🔴")
    async def hard_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.start_quiz_by_difficulty(interaction, "hard", "むずかしい")

game_group = Groups(name="game", description="ゲーム集").create_group()
quiz_group = Groups(name="quiz", description="クイズ集").create_group()

@quiz_group.command(name="integral", description="難易度を選んで積分の計算練習クイズに挑戦します")
async def integral_quiz(ctx: discord.ApplicationContext):
    embed = discord.Embed(title="📐 積分計算クイズ", description="チャレンジする難易度を選択してください！", color=discord.Color.blue())
    view = DifficultySelectView()
    await ctx.respond(embed=embed, view=view)

def greet():
    now = datetime.datetime.now(JST)
    current_hour = now.hour
    if 5 <= current_hour < 11: return "おはようございます"
    elif 11 <= current_hour < 18: return "こんにちは"
    else: return "こんばんは"

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")
    update_status.start()

@tasks.loop(seconds=10)
async def update_status():
    if not client.is_ready():
        return

    ping = round(client.latency * 1000)
    greeting = greet()

    status_text = f"{greeting} | Ping: {ping}ms"

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_text))

@client.event
async def on_application_command_error(
    ctx: discord.ApplicationContext,
    error: discord.DiscordException
):
    original_error = getattr(error, "original", error)
    print(f"コマンドエラー発生: {original_error}")

    await ctx.respond(f"⚠ エラーが発生しました:\n`{original_error}`", ephemeral=True)

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.content == "挨拶して":
        greeting = greet()
        await message.channel.send(f"{message.author.mention}さん、{greeting}")
    if message.content == "こんにちは":
        await message.channel.send(f"{message.author.mention}さん、こんにちは")

@client.slash_command(name="alarm", description="指定した分後にDMでアラームを通知します")
async def alarm(
    ctx: discord.ApplicationContext,
    minutes: float,
    message: str = "時間です",
):
    try:
        minutes_float = float(minutes)
    except ValueError:
        await ctx.respond("数値で入力してください", ephemeral=True) # respod -> respond 修正
        return

    await ctx.respond(f"⏰️ {minutes_float}分後にアラームを設定しました！\nメモ：{message}", ephemeral=True)

    seconds = minutes_float * 60
    await asyncio.sleep(seconds)

    try:
        user = ctx.author
        await user.send(f"🔔** 【アラーム】**{minutes_float}分が経過しました\n📝 メモ: {message}")
    except discord.Forbidden:
        print(f"{ctx.author.name}へのDM送信に失敗しました")

class tetris_setting:
    def __init__(self):
        self.tetris_settings()
    def tetris_settings(self):
        WIDTH = 10
        HEIGHT = 15
        EMPTY = "⬛"
        WALL = "⬜"
        BLOCK = "🟪"
        SETTLED = "🟦"
        SHAPES = {
            "I": [(0, -1), (0, 0), (0, 1), (0, 2)],
            "O": [(0, 0), (0, 1), (1, 0), (1, 1)],
            "T": [(0, 0), (0, -1), (0, 1), (1, 0)],
            "L": [(0, -1), (0, 0), (0, 1), (1, -1)],
        }
        return WIDTH, HEIGHT, EMPTY, WALL, BLOCK, SETTLED, SHAPES
# --- テトリスの設定 ---
WIDTH,  HEIGHT, EMPTY, WALL, BLOCK, SETTLED, SHAPES = tetris_setting().tetris_settings()

class TetrisGame:
    def __init__(self):
        self.grid = [[EMPTY for _ in range(WIDTH)] for _ in range(HEIGHT)]
        self.score = 0
        self.is_game_over = False
        self.spawn_block()

    def spawn_block(self):
        self.current_shape = random.choice(list(SHAPES.keys()))
        self.block_coords = list(SHAPES[self.current_shape])
        self.center_y = 0
        self.center_x = WIDTH // 2

        if self.check_collision(0, 0):
            self.is_game_over = True

    def check_collision(self, dy, dx):
        for py, px in self.block_coords:
            ny = self.center_y + py + dy
            nx = self.center_x + px + dx

            if nx < 0 or nx >= WIDTH or ny >= HEIGHT:
                return True
            if ny >= 0 and self.grid[ny][nx] == SETTLED:
                return True
        return False

    def lock_block(self):
        for py, px in self.block_coords:
            ny = self.center_y + py
            nx = self.center_x + px
            if ny >= 0:
                self.grid[ny][nx] = SETTLED

        new_grid = [row for row in self.grid if any(c == EMPTY for c in row)]
        cleared_lines = HEIGHT - len(new_grid)
        if cleared_lines > 0:
            self.score += cleared_lines * 100
            for _ in range(cleared_lines):
                new_grid.insert(0, [EMPTY for _ in range(WIDTH)])
            self.grid = new_grid

        self.spawn_block()

    def move(self, dy, dx):
        if not self.check_collision(dy, dx):
            self.center_y += dy
            self.center_x += dx
            return True
        return False

    def render(self):
        display_grid = [row[:] for row in self.grid]

        if not self.is_game_over:
            for py, px in self.block_coords:
                ny = self.center_y + py
                nx = self.center_x + px
                if 0 <= ny < HEIGHT and 0 <= nx < WIDTH:
                    display_grid[ny][nx] = BLOCK

        screen = []
        screen.append(WALL * (WIDTH + 2))
        for row in display_grid:
            screen.append(WALL + "".join(row) + WALL)
        screen.append(WALL * (WIDTH + 2))

        screen_text = "\n".join(screen)
        return f"🎮 **DISCORD TETRIS** 🎮\nSCORE: `{self.score}`\n\n{screen_text}"

class TetrisView(View):
    def __init__(self, game: TetrisGame):
        super().__init__(timeout=300)
        self.game = game

    async def update_screen(self, interaction: discord.Interaction):
        if self.game.is_game_over:
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(
                content=f"{self.game.render()}\n❌ **GAME OVER!**", view=self
            )
            return

        await interaction.response.edit_message(
            content=self.game.render(), view=self
        )

    @discord.ui.button(label="◀ 左", style=discord.ButtonStyle.primary, row=0)
    async def left_button(self, button: Button, interaction: discord.Interaction):
        self.game.move(0, -1)
        await self.update_screen(interaction)

    @discord.ui.button(label="⬇ 落下", style=discord.ButtonStyle.success, row=0)
    async def down_button(self, button: Button, interaction: discord.Interaction):
        if not self.game.move(1, 0):
            self.game.lock_block()
        await self.update_screen(interaction)

    @discord.ui.button(label="▶ 右", style=discord.ButtonStyle.primary, row=0)
    async def right_button(self, button: Button, interaction: discord.Interaction):
        self.game.move(0, 1)
        await self.update_screen(interaction)

@game_group.command(name="tetris", description="Discord内でテトリスを開始します")
async def start_tetris(ctx: discord.ApplicationContext):
    game = TetrisGame()
    view = TetrisView(game)

    msg = await ctx.respond(content=game.render(), view=view)

    while not game.is_game_over:
        await asyncio.sleep(2.0)
        if game.is_game_over:
            break

        if not game.move(1, 0):
            game.lock_block()
        try:
            await msg.edit_original_response(content=game.render(), view=view)
        except Exception:
            break

def check_winner(board):
    lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6],
    ]
    for line in lines:
        if board[line[0]] == board[line[1]] == board[line[2]] != " ":
            return board[line[0]]

    if " " not in board:
        return "Draw"

    return None

class TicTacToeButton(discord.ui.Button):
    def __init__(self, index: int, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary, label="ー", row=row
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view

        if view.board[self.index] != " ":
            await interaction.response.send_message(
                "そこには置けません！", ephemeral=True
            )
            return

        view.board[self.index] = "X"
        self.label = "❌"
        self.style = discord.ButtonStyle.danger
        self.disabled = True

        winner = check_winner(view.board)
        if winner:
            await view.end_game(interaction, winner)
            return

        empty_indices = [i for i, x in enumerate(view.board) if x == " "]
        if empty_indices:
            bot_choice = random.choice(empty_indices)
            view.board[bot_choice] = "O"

            bot_button: TicTacToeButton = view.children[bot_choice]
            bot_button.label = "⭕"
            bot_button.style = discord.ButtonStyle.success
            bot_button.disabled = True

        winner = check_winner(view.board)
        if winner:
            await view.end_game(interaction, winner)
            return

        await interaction.response.edit_message(content="あなたの番です！ ❌ を置くマスを選んでください。", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.board = [" " for _ in range(9)]

        for i in range(9):
            row_number = i // 3
            self.add_item(TicTacToeButton(index=i, row=row_number))

    async def end_game(self, interaction: discord.Interaction, winner: str):
        for child in self.children:
            child.disabled = True

        if winner == "X": msg = "🎉 **あなたの勝ちです！**"
        elif winner == "O": msg = "🤖 **Botの勝ちです！**"
        else: msg = "🤝 **引き分けです！**"
        await interaction.response.edit_message(
            content=f"📊 **ゲーム終了！**\n{msg}", view=self
        )

@game_group.command(
    name="tictactoe", description="マルバツゲーム（VS Bot）を開始します"
)
async def start_tictactoe(ctx: discord.ApplicationContext):
    view = TicTacToeView()
    await ctx.respond(
        "❌ **マルバツゲームスタート！** ⭕\nあなたが先攻（❌）です。マスを選んでください！",
        view=view,
    )

commands = {
    "basic": {
        "`/help`": "このヘルプメニューを表示します。",
        "`/ping`": "Botの応答速度（レイテンシ）を計測します。",
        "`/setup_status`": "[管理者用] 管理者の対応状況を表します。",
    },
    "game": {
        "`/game tetris`": "Discord内でテトリスを遊びます。",
        "`/game tictactoe`": "Discord内でマルバツゲームを遊べます",
    },
    "quiz": {
        "`/quiz integral`": "Discord内で積分計算ができます",
        "`/quiz english`": "Discord内で英単語のチェックができます",
    }
}

sorts = {
    "basic": "全般コマンド一覧",
    "game": "🎮 お楽しみコマンド一覧",
    "quiz": "クイズ一覧",
}

class HelpDropdown(Select):
    def __init__(self):
       options = [
           discord.SelectOption(label="basic", description="誰でも使える基本コマンド"),
           discord.SelectOption(label="game", description="テトリスなどのゲーム機能"),
           discord.SelectOption(label="quiz", description="積分計算などのクイズ機能"),
       ]
       super().__init__(placeholder="確認したいカテゴリーを選択してください．．．", max_values=1, min_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        sort = self.values[0]
        command = commands[sort]
        embed = discord.Embed(title=sorts[sort], color=discord.Color.blue())
        for name, value in command.items():
            embed.add_field(name=name, value=value, inline=False)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self.view)

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())

@client.slash_command(name="help", description="Botの使い方とコマンド一覧を表示します")
async def help_command(ctx: discord.ApplicationContext):
    embed = discord.Embed(title="📚 Bot ヘルプメニュー", description="下のドロップダウンメニューから、調べたい機能のカテゴリーを選択してください。", color=discord.Color.light_gray())
    embed.add_field(name="現在のバージョン", value="`v2.0.0` (Py-cord 2026)", inline=True)
    view = HelpView()
    await ctx.respond(embed=embed, view=view, ephemeral=True)

@client.slash_command(name="ping", description="Botの応答速度を計測します") # descirption -> description 修正
async def ping(ctx: discord.ApplicationContext):
    latency = round(client.latency * 1000)
    await ctx.respond(f"🏓 \n・応答速度 (WebSocket): **{latency}ms**")

QUIZ_DATA = {
    "apple": ["りんご", "みかん", "ぶどう", "いちご"],
    "resilient": ["回復力がある", "繊細な", "頑固な", "曖昧な"],
    "meticulous": ["細部まで気配りする", "おおまかな", "急速な", "創造的な"],
    "ubiquitous": ["至る所にある", "珍しい", "一時的な", "古代の"],
}

class QuizView(discord.ui.View):
    def __init__(self, correct_answer: str, choices: list[str]):
        # disable_on_timeout=True でタイムアウト時にボタンを自動無効化
        super().__init__(timeout=60.0, disable_on_timeout=True)
        self.correct_answer = correct_answer
        # 選択肢ボタンを動的に生成してViewに追加
        for choice in choices:
            button = discord.ui.Button(label=choice, style=discord.ButtonStyle.secondary)
            # ボタンクリック時の処理をバインド
            button.callback = self.create_callback(choice)
            self.add_item(button)

    def create_callback(self, choice: str):
        """各ボタン用のクリック時イベント処理"""
        async def button_callback(interaction: discord.Interaction):
            # すべてのボタンを無効化し、正解・不正解に応じて色を変更
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
                    if child.label == self.correct_answer:
                        child.style = discord.ButtonStyle.success  # 正解（緑）
                    elif (
                        child.label == choice
                        and choice != self.correct_answer
                    ):
                        child.style = discord.ButtonStyle.danger  # 選んだ不正解（赤）

            # 正誤判定メッセージの作成
            if choice == self.correct_answer:
                result_msg = f"⭕ **正解！**\n`{choice}` で合っています！"
            else:
                result_msg = f"❌ **不正解...**\n正解は `{self.correct_answer}` でした。"

            # メッセージとボタンの状態を更新
            await interaction.response.edit_message(content=f"{interaction.message.content}\n\n{result_msg}", view=self)
        return button_callback

@quiz_group.command(name="english", description="英単語の四択問題を出題します")
async def quiz(ctx: discord.ApplicationContext):
    # ランダムに1問選択
    word, answers = random.choice(list(QUIZ_DATA.items()))
    correct_answer = answers[0]

    # 選択肢をシャッフル
    choices = answers.copy()
    random.shuffle(choices)
    
    # クイズ用のView（ボタン一覧）を作成
    view = QuizView(correct_answer=correct_answer, choices=choices)
    # スラッシュコマンドに応答
    await ctx.respond(f"【英単語クイズ】\n単語: **{word}** の意味として正しいものを1つ選んでください。", view=view)

class GeminiQuizView(discord.ui.View):
  def __init__(self, correct_answer, choices):
    super().__init__(timeout=60)
    self.correct_answer = correct_answer

    # 選択肢のボタンを生成
    for choice in choices:
      self.add_item(GeminiQuizButton(choice, correct_answer))

class GeminiQuizButton(discord.ui.Button):
  def __init__(self, label, correct_answer):
    super().__init__(label=str(label), style=discord.ButtonStyle.secondary)
    self.correct_answer = correct_answer

    # ボタンが押されたときの処理
  async def callback(self, interaction: discord.Interaction):
    if self.label == str(self.correct_answer):
      await interaction.response.send_message("正解です！🎉", ephemeral=True)
    else:
      await interaction.response.send_message(
          f"残念！正解は **{self.correct_answer}** でした。", ephemeral=True)

    # 回答後にすべてのボタンを無効化
    for child in self.view.children:
      child.disabled = True
    await interaction.message.edit(view=self.view)


@quiz_group.command(name="trigo", description="三角関数の問題を出題します")
async def gemini_quiz(ctx: discord.ApplicationContext):
  await ctx.defer()
    
  prompt = """
    高校数学Iの三角比（0°〜180°の sin, cos, tan の値など）に関する基本問題を1問作成してください。
    必ず以下のJSON形式のみで出力してください（マークダウンの ```json ... ``` は付けず、純粋なJSON文字列だけにしてください）。

    {
      "question": "問題文（例：sin 135° の値を求めよ）",
      "correct_answer": "正解の数値や値（例：1/\\sqrt{2} など）",
      "choices": ["選択肢1", "選択肢2", "選択肢3", "選択肢4"]
    }
    ※ choicesには正解を含め、4つの選択肢をシャッフルした状態で入れてください。
    """
  try:
    # Geminiモデルの呼び出し (Flashモデルを使用)
    response = ai.models.generate_content(model="gemini-2.5-flash", contents=prompt)
      
    # JSONとしてパース
    data = json.loads(response.text.strip())
    q_text = data["question"]
    correct = data["correct_answer"]
    choices = data["choices"]
      
    # 選択肢をランダムに並び替え
    random.shuffle(choices)
    view = GeminiQuizView(correct, choices)

    await ctx.followup.send(f"**【Gemini特製：数学I 三角比クイズ】**\n{q_text}", view=view)
      
  except Exception as e:
    await ctx.followup.send(f"問題の生成中にエラーが発生しました: {e}", ephemeral=True)

class DownloadView(discord.ui.View):
    def __init__(self, file_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="ダウンロード", style=discord.ButtonStyle.link, url=file_url, emoji="📥"))

@client.slash_command(name="upload", description="ファイルをアップロードして詳細とともに共有します")
async def upload_file(
    ctx: discord.ApplicationContext,
    file: discord.Attachment,
    caption: str = "アップロードされたファイル"
):
    await ctx.defer()
    try:
        file_url = file.url
        file_io = io.BytesIO(await file.read())
        discord_file = discord.File(fp=file_io, filename=file.filename)
        
        embed = discord.Embed(
            title="📁 ファイルアップロード",
            description=f"**ファイル名:** `{file.filename}`\n**サイズ:** `{file.size / 1024:.2f} KB`\n**説明:** {caption}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"アップロード者: {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        view = DownloadView(file_url)
        await ctx.followup.send(embed=embed, file=discord_file, view=view)
    except Exception as e:
        await ctx.followup.send(f"⚠️ ファイルのアップロード処理中にエラーが発生しました: {e}", ephemeral=True)

client.run(token)
