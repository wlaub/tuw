using System;
using System.IO;
using System.Text;
using System.Reflection;
using System.Runtime.InteropServices;
using System.IO.MemoryMappedFiles;
using Microsoft.Xna.Framework;

using Monocle;

using MonoMod.Utils;

using Celeste;
using Celeste.Mod;


namespace Celeste.Mod.TheUltimateWednesday {

    public struct HeaderState
    {
        public uint sequence;
        public double timestamp;
        public long time;
        public int deaths;
        public string room;

        public byte[] to_bytes()
        {
            byte[] room_buffer = Encoding.ASCII.GetBytes(room);
            int size = 8+8+4+4+room_buffer.Length+1;
            byte[] result = new byte[size];

            BitConverter.GetBytes(sequence).CopyTo(result, 0);
            BitConverter.GetBytes(timestamp).CopyTo(result, 4);
            BitConverter.GetBytes(time).CopyTo(result, 12);
            BitConverter.GetBytes(deaths).CopyTo(result, 20);
            //Encoding.ASCII doesn't return a null-terminated string...
            room_buffer.CopyTo(result, 24);
            result[size-1] = 0;

            return result;
        }

    }

    public struct PlayerState
    {
        public float xpos;
        public float ypos;
        public float xvel;
        public float yvel;
        public float stamina;
        public float xlift;     //liftspeed
        public float ylift;

        public int state;
        public int dashes;

        public byte control_flags;

        public byte status_flags;

        public byte[] to_bytes()
        {
            byte[] result = new byte[38];

            //what was wrong with struct.pack???
            BitConverter.GetBytes(xpos).CopyTo(result, 0);
            BitConverter.GetBytes(ypos).CopyTo(result, 4);
            BitConverter.GetBytes(xvel).CopyTo(result, 8);
            BitConverter.GetBytes(yvel).CopyTo(result, 12);
            BitConverter.GetBytes(stamina).CopyTo(result, 16);
            BitConverter.GetBytes(xlift).CopyTo(result, 20);
            BitConverter.GetBytes(ylift).CopyTo(result, 24);
            BitConverter.GetBytes(state).CopyTo(result, 28);
            BitConverter.GetBytes(dashes).CopyTo(result, 32);
            result[36] = control_flags;
            result[37] = status_flags;

            return result;
        }

        public void pack_control_flags(bool dead, bool control, bool cutscene, bool transition, bool paused)
        {
            control_flags = (byte)(
                  (dead ? 1 << 7 : 0)
                | (control ? 1 << 6 : 0)
                | (cutscene ? 1 << 5 : 0)
                | (transition ? 1 << 4 : 0)
                | (paused ? 1 << 3 : 0)
                | (false ? 1 << 2 : 0)
                | (false ? 1 << 1 : 0)
                | (false ? 1 : 0)
                );
        }

        public void pack_status_flags(bool holding, bool crouched, bool facing_left, 
                                      bool wall_left, bool wall_right, bool coyote, 
                                      bool safe_ground, bool ground)
        {
            status_flags = (byte)(
                  (holding ? 1 << 7 : 0)
                | (crouched ? 1 << 6 : 0)
                | (facing_left ? 1 << 5 : 0)
                | (wall_left ? 1 << 4 : 0)
                | (wall_right ? 1 << 3 : 0)
                | (coyote ? 1 << 2 : 0)
                | (safe_ground ? 1 << 1 : 0)
                | (ground ? 1 : 0)
            );
        }



    }

    public struct InputState
    {
       
        public byte button_flags;
        public byte direction_flags;
        public float xaim;
        public float yaim;

        public byte[] to_bytes()
        {
            byte[] result = new byte[10];

            //what was wrong with struct.pack???
            result[0] = button_flags;
            result[1] = direction_flags;
            BitConverter.GetBytes(xaim).CopyTo(result, 2);
            BitConverter.GetBytes(yaim).CopyTo(result, 6);

            return result;
        }



        public void pack_buttons(bool quick_restart, bool pause, bool escape, bool crouch_dash,
                                 bool talk, bool grab, bool dash, bool jump)
        {
            button_flags = (byte)(
              (quick_restart ? 1 << 7 : 0)
                | (pause ? 1 << 6 : 0)
                | (escape ? 1 << 5 : 0)
                | (crouch_dash ? 1 << 4 : 0)
                | (talk ? 1 << 3 : 0)
                | (grab ? 1 << 2 : 0)
                | (dash ? 1 << 1 : 0)
                | (jump ? 1 : 0)
            );
        }
        public void pack_directions(bool up, bool down, bool left, bool right)
        {
            direction_flags = (byte)(
                  (false ? 1 << 7 : 0)
                | (false ? 1 << 6 : 0)
                | (false ? 1 << 5 : 0)
                | (false ? 1 << 4 : 0)
                | (up ? 1 << 3 : 0)
                | (down ? 1 << 2 : 0)
                | (left ? 1 << 1 : 0)
                | (right ? 1 : 0)
            );
        }
 
 
    }

    public struct TransientState
    {
        
        //7  gain_follower;
        //6
        //5  heart_get;
        //4  tape_get;
        //3  key_lost;
        //2  key_collected;
        //1  seeds_collected;
        //0  berry_collected;

        //7  clutter switch
        //6  text box
        //5  player spawn
        //4  flag_change;
        //3  fake_wall; //not implemented, can't find a place to hook
        //2  cutscene;
        //1  dash_block;
        //0  respawn change

        public byte collection_flags;
        public byte state_flags; 

        public void clear()
        {
            collection_flags = 0;
            state_flags = 0;
        }

        public bool has()
        {
            return (collection_flags | state_flags) != 0;
        }

        public byte[] to_bytes()
        {
            byte[] result = new byte[4];

            result[0] = 0x01; //transient packet type
            result[1] = 0x02; //packet length
            result[2] = collection_flags;
            result[3] = state_flags;

            return result;
        }



    }

    public struct StreamState
    {
        public string map_name;
        public string chapter_name;

        public byte[] to_bytes()
        {
            int size = map_name.Length+chapter_name.Length+2;

            byte[] result = new byte[size];

            int offset = 0;
            Encoding.ASCII.GetBytes(map_name).CopyTo(result, offset);
            offset += map_name.Length+1;
            Encoding.ASCII.GetBytes(chapter_name).CopyTo(result, offset);
            offset += chapter_name.Length+1;

            return result;
        }

    }

    public class TheUltimateWednesdayModule : EverestModule {
        public static TheUltimateWednesdayModule Instance { get; private set; }

        public override Type SettingsType => typeof(TheUltimateWednesdayModuleSettings);
        public static TheUltimateWednesdayModuleSettings Settings => (TheUltimateWednesdayModuleSettings) Instance._Settings;

        public override Type SessionType => typeof(TheUltimateWednesdayModuleSession);
        public static TheUltimateWednesdayModuleSession Session => (TheUltimateWednesdayModuleSession) Instance._Session;

        public static HeaderState header_state;
        public static PlayerState player_state;
        public static InputState input_state;
        public static StreamState stream_state;
        public static TransientState trans_state;
        public static string map_name;
        public static string room_name;
        public static uint sequence = 0;

        public static FileStream stream;
        public static BinaryWriter fp = null;

        public static FileStream mm_stream;
        public static MemoryMappedFile mm_file;

        public static string output_dir;
        public static bool in_level;
        public static bool first_packet;

        public static Vector2? respawn = null;

        public TheUltimateWednesdayModule() {
            Instance = this;
#if DEBUG
            // debug builds use verbose logging
            Logger.SetLogLevel(nameof(TheUltimateWednesdayModule), LogLevel.Verbose);
#else
            // release builds use info logging to reduce spam in log files
            Logger.SetLogLevel(nameof(TheUltimateWednesdayModule), LogLevel.Info);
#endif

            output_dir = Path.Combine(Everest.PathGame, "tuw_outputs");
            Directory.CreateDirectory(output_dir);

            open_mm_file();

        }

        public static void open_mm_file() 
        {
            //I don't wanna deal with figuring out reasonable ipc in c#
            //https://github.com/EverestAPI/CelesteTAS-EverestInterop/blob/master/StudioCommunication/StudioCommunicationBase.cs
            string target = "celeste_tuw";
            bool wine = File.Exists("/proc/self/exe") && Environment.OSVersion.Platform.HasFlag(PlatformID.Win32NT);
            bool non_windows = !Environment.OSVersion.Platform.HasFlag(PlatformID.Win32NT);

            int buffer_size = 0x1000;

            if (wine || non_windows) {
                string filename = Path.Combine("/tmp", $"{target}.share");

                if (File.Exists(filename)) {
                    mm_stream = new FileStream(filename, FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite);
                } else {
                    mm_stream = new FileStream(filename, FileMode.Create, FileAccess.ReadWrite, FileShare.ReadWrite);
                    mm_stream.SetLength(buffer_size);
                }

                mm_file = MemoryMappedFile.CreateFromFile(mm_stream, null, mm_stream.Length, MemoryMappedFileAccess.ReadWrite, null, HandleInheritability.None,
                    true);
            } else {
                mm_file = MemoryMappedFile.CreateOrOpen(target, buffer_size);
            }
        }

        public static void mm_write(byte[] buffer)
        {
            if(mm_file == null)
            { return; }
            using(MemoryMappedViewStream stream = mm_file.CreateViewStream())
            {
                BinaryWriter writer = new(stream);
                stream.Position = 0;
                writer.Write(buffer);
            }
        }

        public override void Load() {
            Everest.Events.Level.OnEnter += on_enter_hook;
            Everest.Events.Level.OnExit += on_exit_hook;
            On.Monocle.Engine.Update += Update;

            Everest.Events.Player.OnSpawn += on_spawn_hook;

            //Transients
            //Collection
            On.Celeste.Leader.GainFollower += gain_follower_hook;
            On.Celeste.StrawberrySeed.OnAllCollected += seeds_hook;
            On.Celeste.Strawberry.OnCollect += berry_hook;
            On.Celeste.Key.OnPlayer += key_hook;
            On.Celeste.Key.RegisterUsed += door_hook;
            On.Celeste.Cassette.OnPlayer += tape_hook;
            On.Celeste.HeartGem.Collect += heart_hook;
            //7

            //State Change
            On.Celeste.ClutterSwitch.BePressed += clutter_switch_hook;
            On.Celeste.DashBlock.RemoveAndFlagAsGone += dash_block_hook;
            //Fake walls
            On.Celeste.Session.SetFlag += flag_hook;
            On.Celeste.CutsceneEntity.Start += cutscene_hook;
            On.Celeste.MiniTextboxTrigger.Trigger += text_hook;
            //6
            //7


        }

        public override void Unload() {
            On.Monocle.Engine.Update -= Update;
            Everest.Events.Level.OnEnter -= on_enter_hook;
            Everest.Events.Level.OnExit -= on_exit_hook;

            Everest.Events.Player.OnSpawn -= on_spawn_hook;

            //Transients
            On.Celeste.Leader.GainFollower -= gain_follower_hook;
            On.Celeste.StrawberrySeed.OnAllCollected -= seeds_hook;
            On.Celeste.Strawberry.OnCollect -= berry_hook;
            On.Celeste.Key.OnPlayer -= key_hook;
            On.Celeste.Cassette.OnPlayer -= tape_hook;
            On.Celeste.ClutterSwitch.BePressed -= clutter_switch_hook;
            On.Celeste.DashBlock.RemoveAndFlagAsGone -= dash_block_hook;
            On.Celeste.HeartGem.Collect -= heart_hook;
            On.Celeste.Key.RegisterUsed -= door_hook;
            On.Celeste.CutsceneEntity.Start -= cutscene_hook;
            On.Celeste.Session.SetFlag -= flag_hook;
            On.Celeste.MiniTextboxTrigger.Trigger -= text_hook;

        }

        public void on_spawn_hook(Player player)
        {
            trans_state.state_flags |= 0x01<<5;
        }

        public void gain_follower_hook(On.Celeste.Leader.orig_GainFollower orig, Leader self, Follower follower)
        {
            orig(self, follower);
            trans_state.collection_flags |= 0x01<<7;
        }

        public void seeds_hook(On.Celeste.StrawberrySeed.orig_OnAllCollected orig, StrawberrySeed self)
        {
            trans_state.collection_flags |= 0x01<<1;
            orig(self);
        }
        public void berry_hook(On.Celeste.Strawberry.orig_OnCollect orig, Strawberry self)
        {
            trans_state.collection_flags |= 0x01;
            orig(self);
        }
        public void key_hook(On.Celeste.Key.orig_OnPlayer orig, Key self, Player player)
        {
            trans_state.collection_flags |= 0x01<<2;
            orig(self, player);
        }
        public void tape_hook(On.Celeste.Cassette.orig_OnPlayer orig, Cassette self, Player player)
        {
            trans_state.collection_flags |= 0x01<<4;
            orig(self, player);
        }
        public void clutter_switch_hook(On.Celeste.ClutterSwitch.orig_BePressed orig, ClutterSwitch self)
        {
            trans_state.state_flags |= 0x01<<7;
            orig(self);
        }
        public void dash_block_hook(On.Celeste.DashBlock.orig_RemoveAndFlagAsGone orig, DashBlock self)
        {
            trans_state.state_flags |= 0x01<<1;
            orig(self);
        }
        public void heart_hook(On.Celeste.HeartGem.orig_Collect orig, HeartGem self, Player player)
        {
            trans_state.collection_flags |= 0x01<<5;
            orig(self, player);
        }
        public void door_hook(On.Celeste.Key.orig_RegisterUsed orig, Key self)
        {
            trans_state.collection_flags |= 0x01<<3;
            orig(self);
        }
        public void cutscene_hook(On.Celeste.CutsceneEntity.orig_Start orig, CutsceneEntity self)
        {
            trans_state.state_flags |= 0x01<<2;
            orig(self);
        }
        public void text_hook(On.Celeste.MiniTextboxTrigger.orig_Trigger orig, MiniTextboxTrigger self)
        {
            DynamicData data = new DynamicData(self);
            bool before = data.Get<bool>("triggered");
            orig(self);
            bool after = data.Get<bool>("triggered");
            if(!before && after)
            {
                trans_state.state_flags |= 0x01<<6;
            }
        }

        public void flag_hook(On.Celeste.Session.orig_SetFlag orig, Session self, string flag, bool set_to)
        {
            if(self.GetFlag(flag) != set_to)
            {
                trans_state.state_flags |= 0x01<<4;
            }
            orig(self, flag, set_to);
        }

        public string make_string_more_better(string input)
        {
            string result;
            result = input.Replace(Path.DirectorySeparatorChar, '_');
            result = result.Replace(Path.AltDirectorySeparatorChar, '_');
            result = result.Replace('-', '_');
            result = result.Replace(' ', '_');
            return result;

        }

        private void on_enter_hook(Session session, bool fromSaveData)
        {
            in_level = true;
            map_name = make_string_more_better(session.Area.SID);

            string mod_name = make_string_more_better(session.Area.LevelSet);

            stream_state.chapter_name = Dialog.Get(map_name);
            stream_state.map_name = Dialog.Get(mod_name);

            if(Settings.write_file)
            {
                open_dump_file();
            }
            Logger.Log(LogLevel.Info, "tuw", map_name);

        }

        public static void open_dump_file()
        {
            if(!in_level) return;

            string outfile = Path.Combine(output_dir, DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss_") + map_name + ".dump");

            if(fp != null)
            {
                fp.Close();
                stream.Close();
            }

            //what was wrong with with open(filename, 'wb') as fp:?
            stream = File.Open(outfile, FileMode.Create);
            fp = new BinaryWriter(stream);
            first_packet = true;

        }

        public static void close_dump_file()
        {
            if(fp == null) return;
            fp.Flush();
            fp.Close();
            stream.Close();
            fp = null;
 
        }

        private void on_exit_hook(Level level, LevelExit exit, LevelExit.Mode mode, Session session, HiresSnow snow)
        {
            in_level = false;
            close_dump_file();
        }

        public static void Update(On.Monocle.Engine.orig_Update orig, Engine self, GameTime gameTime)
        {
            orig(self, gameTime);

            bool header_state_valid = update_header_state();
            bool player_state_valid = update_player_state();
            bool input_state_valid = update_input_state();

            if(player_state_valid)
            {
                header_state.sequence = sequence;
                sequence += 1;
                byte[] header = header_state.to_bytes();
                byte[] player = player_state.to_bytes();
                byte[] input = input_state.to_bytes();
                byte[] transient_info = trans_state.to_bytes();
                byte[] stream_info = stream_state.to_bytes();

                bool has_transient = trans_state.has();
                trans_state.clear();

                ushort size = (ushort)(header.Length+player.Length+input.Length);
                byte[] size_header = BitConverter.GetBytes(size);

                ushort mm_size = (ushort)(size + transient_info.Length + stream_info.Length);
                byte[] mm_size_header = BitConverter.GetBytes(mm_size);

                if(has_transient)
                {   //Include the transient output in the dump buffer, update size accordingly
                    size += (ushort)transient_info.Length;
                    size_header = BitConverter.GetBytes(size);
                }

                byte[] buffer = new byte[2 + mm_size];
                int offset = 0;
                size_header.CopyTo(buffer, offset);
                offset += 2;
                header.CopyTo(buffer, offset); offset += header.Length;
                player.CopyTo(buffer, offset); offset += player.Length;
                input.CopyTo(buffer, offset); offset += input.Length;
                transient_info.CopyTo(buffer, offset); offset += transient_info.Length;
                stream_info.CopyTo(buffer, offset); offset += stream_info.Length;

                //write out
                if(fp == null && Settings.write_file)
                {
                    open_dump_file();
                }
                if(fp != null)
                {
                    if(first_packet)
                    {
                        first_packet = false;
                        buffer[0] = mm_size_header[0];
                        buffer[1] = mm_size_header[1];
                        fp.Write(buffer);
                    }
                    else
                    {
                        fp.Write(buffer, 0, size+2);
                    }
                    if(!Settings.write_file)
                    {
                        close_dump_file();
                    }
 
                }
                buffer[0] = mm_size_header[0];
                buffer[1] = mm_size_header[1];

                mm_write(buffer);

            }
        }

        public static bool update_header_state()
        {
            header_state.timestamp = DateTime.UtcNow.Subtract(new DateTime(1970, 1, 1)).TotalSeconds;
            if (Engine.Scene is Level level)
            {
                header_state.time = level.Session.Time;
                header_state.deaths = level.Session.Deaths;
                header_state.room = level.Session.Level;
            }
            return true;
        }

        public static bool update_player_state()
        {
            if (Engine.Scene is Level level)
            {
                Player player = level.Tracker.GetEntity<Player>();
                if (player == null)
                {
                    return false;
                }

                player_state.xpos = player.Position.X;
                player_state.ypos = player.Position.Y;

                player_state.xvel = player.Speed.X;
                player_state.yvel = player.Speed.Y;

                player_state.stamina = player.Stamina;

                player_state.xlift = player.LiftSpeed.X;
                player_state.ylift = player.LiftSpeed.Y;


                player_state.dashes = player.Dashes;
                player_state.state = player.StateMachine.State;

                bool dead = player.Dead;
                bool control = player.InControl;
                bool cutscene = level.InCutscene;
                bool transition = level.Transitioning;
                bool paused = level.Paused;
                player_state.pack_control_flags(dead, control, cutscene, transition, paused);

                bool holding = (player.Holding != null);
                bool ground = player.LoseShards;
                bool safe_ground = player.OnSafeGround; 
                bool crouched = player.Ducking;

                bool facing_left = (player.Facing == Facings.Left);

                bool coyote = (float)(player.GetType().GetField("jumpGraceTimer", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(player)) > 0;
                //what a hideous language. private variables are literally fascism
                var walljumpcheck = player.GetType().GetMethod("WallJumpCheck", BindingFlags.Instance | BindingFlags.NonPublic);
                object[] param = new object[] {-1};
                bool wall_left = (bool)(walljumpcheck.Invoke(player, param));
                param[0] = 1;
                bool wall_right = (bool)(walljumpcheck.Invoke(player, param));

                player_state.pack_status_flags(holding, crouched, facing_left, wall_left, wall_right, coyote, safe_ground, ground);

                if(level.Session.RespawnPoint != respawn)
                {
                    respawn = level.Session.RespawnPoint;
                    trans_state.state_flags |= 1;
                }

                return true;
            }
            else
            {
                return false;
            }
 
        }

        public static bool update_input_state()
        {
            bool escape = Input.ESC.Check;
            bool pause = Input.Pause.Check;
            bool quick_restart = Input.QuickRestart.Check;
            bool crouch_dash = Input.CrouchDash.Check;
            bool talk = Input.Talk.Check;
            bool grab = Input.Grab.Check;
            bool dash = Input.Dash.Check;
            bool jump = Input.Jump.Check;
   
            input_state.pack_buttons(quick_restart, pause, escape, crouch_dash, talk, grab, dash, jump) ;

            bool left = Input.MoveX == 1;
            bool right = Input.MoveX == -1;
            bool up = Input.MoveY == 1;
            bool down = Input.MoveY == -1;

            input_state.pack_directions(up, down, left, right);

            input_state.xaim = Input.Aim.Value.X;
            input_state.yaim = Input.Aim.Value.Y;

            return true;
        }

    }
}
