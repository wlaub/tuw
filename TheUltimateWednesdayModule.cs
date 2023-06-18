using System;
using System.IO;
using System.Text;
using System.Reflection;
using System.Runtime.InteropServices;
using Microsoft.Xna.Framework;

using Monocle;

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

        public void pack_control_flags(bool dead, bool control, bool cutscene, bool transition)
        {
            control_flags = (byte)(
                  (dead ? 1 << 7 : 0)
                | (control ? 1 << 6 : 0)
                | (cutscene ? 1 << 5 : 0)
                | (transition ? 1 << 4 : 0)
                | (false ? 1 << 3 : 0)
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

    public class TheUltimateWednesdayModule : EverestModule {
        public static TheUltimateWednesdayModule Instance { get; private set; }

        public override Type SettingsType => typeof(TheUltimateWednesdayModuleSettings);
        public static TheUltimateWednesdayModuleSettings Settings => (TheUltimateWednesdayModuleSettings) Instance._Settings;

        public override Type SessionType => typeof(TheUltimateWednesdayModuleSession);
        public static TheUltimateWednesdayModuleSession Session => (TheUltimateWednesdayModuleSession) Instance._Session;

        public static HeaderState header_state;
        public static PlayerState player_state;
        public static InputState input_state;
        public static string map_name;
        public static string room_name;
        public static uint sequence = 0;

        public static FileStream stream;
        public static BinaryWriter fp = null;

        public string output_dir;
        public bool in_level;

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
        }

        public override void Load() {
            Everest.Events.Level.OnEnter += on_enter_hook;
            Everest.Events.Level.OnExit += on_exit_hook;
            On.Monocle.Engine.Update += Update;
        }

        public override void Unload() {
            Everest.Events.Level.OnEnter -= on_enter_hook;
            Everest.Events.Level.OnExit -= on_exit_hook;
            On.Monocle.Engine.Update -= Update;
        }


        private void on_enter_hook(Session session, bool fromSaveData)
        {
            in_level = true;
            map_name = session.Area.SID.Replace(Path.DirectorySeparatorChar, '_');
            map_name = map_name.Replace(Path.AltDirectorySeparatorChar, '_');

            string outfile = Path.Combine(output_dir, DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss_") + ".dump");

            if(fp != null)
            {
                fp.Close();
                stream.Close();
            }

            //what was wrong with with open(filename, 'wb') as fp:?
            stream = File.Open(outfile, FileMode.Create);
            fp = new BinaryWriter(stream);

            Logger.Log(LogLevel.Info, "tuw", map_name);

        }

        private void on_exit_hook(Level level, LevelExit exit, LevelExit.Mode mode, Session session, HiresSnow snow)
        {
            in_level = false;
            fp.Flush();
            fp.Close();
            stream.Close();
            fp = null;
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
            Logger.Log(LogLevel.Info, "tuw", ":" + player.Length + " " + input.Length);
                ushort size = (ushort)(header.Length+player.Length+input.Length);
                byte[] size_header = BitConverter.GetBytes(size);
                byte[] buffer = new byte[2 + size];
                size_header.CopyTo(buffer, 0);
                header.CopyTo(buffer, 2);
                player.CopyTo(buffer, 2+header.Length);
                input.CopyTo(buffer, 2+header.Length+player.Length);

                //write out
                if(fp != null)
                {
                    fp.Write(buffer);
                }

            }
        }


        //Why is this language so obsessed with making trivial tasks inconvenient?
        public static byte[] getBytes(PlayerState str) {
            int size = Marshal.SizeOf(str);
            size = 38; //Idk why Marshal.SizeOf gives 40. That's the wrong answer
            byte[] arr = new byte[size];

            IntPtr ptr = IntPtr.Zero;
            try
            {
                ptr = Marshal.AllocHGlobal(size);
                Marshal.StructureToPtr(str, ptr, true);
                Marshal.Copy(ptr, arr, 0, size);
            }
            finally
            {
                Marshal.FreeHGlobal(ptr);
            }
            return arr;
        }
        //Why is this language so obsessed with making trivial tasks inconvenient?
        public static byte[] getBytes(InputState str) {
            int size = Marshal.SizeOf(str);
            byte[] arr = new byte[size];

            IntPtr ptr = IntPtr.Zero;
            try
            {
                ptr = Marshal.AllocHGlobal(size);
                Marshal.StructureToPtr(str, ptr, true);
                Marshal.Copy(ptr, arr, 0, size);
            }
            finally
            {
                Marshal.FreeHGlobal(ptr);
            }
            return arr;
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
                player_state.pack_control_flags(dead, control, cutscene, transition);

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
