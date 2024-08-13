
namespace Celeste.Mod.TheUltimateWednesday {
    public class TheUltimateWednesdayModuleSettings : EverestModuleSettings {

        [SettingName("modoptions_tuw_write_file")]
        [SettingSubText("modoptions_tuw_write_file_desc")]
        public bool write_file {get; set;} = false;

        [SettingName("modoptions_tuw_mark_0")]
        [SettingSubText("modoptions_tuw_mark_0_desc")]
        public ButtonBinding mark_button_0 {get; set;} = new();
        [SettingName("modoptions_tuw_mark_1")]
        [SettingSubText("modoptions_tuw_mark_1_desc")]
        public ButtonBinding mark_button_1 {get; set;} = new();
        [SettingName("modoptions_tuw_mark_2")]
        [SettingSubText("modoptions_tuw_mark_2_desc")]
        public ButtonBinding mark_button_2 {get; set;} = new();
        [SettingName("modoptions_tuw_mark_3")]
        [SettingSubText("modoptions_tuw_mark_3_desc")]
        public ButtonBinding mark_button_3 {get; set;} = new();




    }
}
