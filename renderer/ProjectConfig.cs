using System.Globalization;
using System.Reflection;
using System.Text.RegularExpressions;
using OpenTK;
using OpenTK.Graphics;
using StorybrewCommon.Storyboarding;

namespace FullExport;

sealed record ConfigValue(string Name, string Value, int Start, int Length);
sealed record LayerConfig(string Id, string Name, OsbLayer Layer, bool Visible);
sealed record EffectConfig(string File, string Script, string Name, Dictionary<string, ConfigValue> Values, List<LayerConfig> Layers)
{
    public void Apply(object generator)
    {
        foreach (var entry in Values.Values)
        {
            var field = generator.GetType().GetField(entry.Name); if (field == null) continue;
            var type = field.FieldType; object value;
            if (type.IsEnum) value = Enum.ToObject(type, int.Parse(entry.Value, CultureInfo.InvariantCulture));
            else if (type == typeof(Vector2)) { var p = entry.Value.Split(',').Select(v => float.Parse(v, CultureInfo.InvariantCulture)).ToArray(); value = new Vector2(p[0], p[1]); }
            else if (type == typeof(Color4)) { var p = entry.Value.Split(',').Select(v => float.Parse(v, CultureInfo.InvariantCulture)).ToArray(); value = new Color4(p[0], p[1], p[2], p[3]); }
            else value = Convert.ChangeType(entry.Value, type, CultureInfo.InvariantCulture);
            field.SetValue(generator, value);
        }
    }
}

static class ProjectConfig
{
    public static List<EffectConfig> Read(Dictionary<string, string> texts)
    {
        var result = new List<EffectConfig>();
        foreach (var file in texts.Where(p => p.Key.StartsWith(".sbrew/effect.") && p.Key.EndsWith(".yaml")))
        {
            var text = file.Value; string Top(string name) => Regex.Match(text, "(?m)^" + name + ": \\\"([^\\\"]*)\\\"").Groups[1].Value;
            var values = new Dictionary<string, ConfigValue>();
            foreach (Match m in Regex.Matches(text, "(?m)^  (\\w+):\\r?\\n    Type: \\\"[^\\\"]*\\\"\\r?\\n    Value: \\\"([^\\\"]*)\\\""))
                values[m.Groups[1].Value] = new(m.Groups[1].Value, m.Groups[2].Value, m.Groups[2].Index, m.Groups[2].Length);
            var layers = new List<LayerConfig>();
            foreach (Match m in Regex.Matches(text, "(?m)^  ([a-f0-9]{32}):\\r?\\n    Name: \\\"([^\\\"]*)\\\"\\r?\\n    OsbLayer: (\\w+)\\r?\\n    DiffSpecific: \\w+\\r?\\n    Visible: (Yes|No)"))
                layers.Add(new(m.Groups[1].Value, m.Groups[2].Value, Enum.Parse<OsbLayer>(m.Groups[3].Value), m.Groups[4].Value == "Yes"));
            result.Add(new(file.Key, Top("Script"), Top("Name"), values, layers));
        }
        return result;
    }
}