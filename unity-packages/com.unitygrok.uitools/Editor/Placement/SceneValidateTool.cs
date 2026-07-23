using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;

namespace UnityGrok.UITools.Placement
{
    [McpForUnityTool("scene_validate")]
    public static class SceneValidateTool
    {
        public class Parameters
        {
            [ToolParameter("Substring on object name/hierarchy path to scope the scan; omit for whole scene", Required = false)]
            public string filter { get; set; }

            [ToolParameter("Explicit hierarchy paths (or leaf names) to validate", Required = false)]
            public string[] targets { get; set; }

            [ToolParameter("Fallback ground plane Y when no collider is found below an object", Required = false)]
            public float? ground_y { get; set; }

            [ToolParameter("Grounded + penetration tolerance in meters (default 0.05)", Required = false)]
            public float? ground_tolerance { get; set; }

            [ToolParameter("Max downward ray distance when searching for ground (default 5)", Required = false)]
            public float? ground_search { get; set; }

            [ToolParameter("Return every object in the response, not just defective ones", Required = false)]
            public bool? include_all { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            var opt = new SceneValidator.Options();

            var filter = @params?["filter"]?.ToString();
            if (!string.IsNullOrEmpty(filter)) opt.filter = filter;

            var targets = @params?["targets"] as JArray;
            if (targets != null && targets.Count > 0)
                opt.targets = targets.Select(t => t.ToString()).ToList();

            var groundY = @params?["ground_y"];
            if (groundY != null && groundY.Type != JTokenType.Null)
            {
                opt.hasGroundY = true;
                opt.groundY = groundY.Value<float>();
            }

            var tol = @params?["ground_tolerance"];
            if (tol != null && tol.Type != JTokenType.Null) opt.groundTolerance = tol.Value<float>();

            var search = @params?["ground_search"];
            if (search != null && search.Type != JTokenType.Null) opt.groundSearch = search.Value<float>();

            bool includeAll = ParamCoercion.CoerceBool(@params?["include_all"], false);

            SceneValidator.Report report;
            try
            {
                report = SceneValidator.Validate(opt);
            }
            catch (System.Exception ex)
            {
                return new ErrorResponse($"scene_validate_failed: {ex.Message}");
            }

            var floating = report.objects.Where(o => o.floating).ToList();
            var buried = report.objects.Where(o => o.buried).ToList();

            object data = new
            {
                scene = report.scene,
                objectCount = report.objectCount,
                summary = report.summary,
                floating,
                buried,
                penetrationPairs = report.penetrationPairs,
                containmentPairs = report.containmentPairs,
                invalid = report.invalid,
                reportFile = report.reportFile,
                allObjects = includeAll ? report.objects : null
            };

            int defects = floating.Count + buried.Count + report.penetrationPairs.Count + report.invalid.Count;
            string msg = defects == 0
                ? $"scene_validate: {report.objectCount} objects, no defects"
                : $"scene_validate: {report.objectCount} objects, {floating.Count} floating, {buried.Count} buried, {report.penetrationPairs.Count} penetrating pairs, {report.invalid.Count} invalid";
            return new SuccessResponse(msg, data);
        }
    }
}
