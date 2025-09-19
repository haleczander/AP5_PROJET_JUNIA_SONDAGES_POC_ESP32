package junia.isen.ap5.poc_esp32;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class PocEsp32Application extends SpringBootServletInitializer {

    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
        return application.sources(PocEsp32Application.class);
    }

    public static void main(String[] args) {
        SpringApplication.run(PocEsp32Application.class, args);
    }

    private List<Map<String, Object>> projects = createProjects();

    private List<String> authorizedRfids = List.of(
        "39:68:B3:B9:5B"
    );

    private List<Map<String, Object>> createProjects() {
        List<Map<String, Object>> projects = new ArrayList<>();

        // Noms en dur
        String[] names = {
                "Apollo", "Zephyr", "Orion", "Luna", "Nova",
                "Pegasus", "Aurora", "Vega", "Atlas", "Sirius",
                "Phoenix", "Titan"
        };

        for (int i = 1; i <= 12; i++) {
            Map<String, Object> project = new HashMap<>();
            project.put("id", i);
            project.put("projet_nom", names[i - 1]);
            project.put("nb_votes", 0); // votes initiaux à 0
            projects.add(project);
        }

        return projects;
    }



    // --- Endpoints REST standardisés ---

    @GetMapping("/projects")
    public ResponseEntity<List<Map<String, Object>>> getProjects() {
        return ResponseEntity.ok(projects); // 200 OK
    }

    @PostMapping("/vote")
    public ResponseEntity<Map<String, Object>> voteMultiple(@RequestBody Map<Integer, Integer> votes) {
        Map<String, Object> response = new HashMap<>();
        boolean anyError = false;

        for (Map.Entry<Integer, Integer> entry : votes.entrySet()) {
            Integer projectId = entry.getKey();
            Integer votesToAdd = entry.getValue();

            boolean found = false;
            for (Map<String, Object> project : projects) {
                if (project.get("id").equals(projectId)) {
                    int currentVotes = (int) project.get("nb_votes");
                    project.put("nb_votes", currentVotes + votesToAdd);
                    found = true;
                    break;
                }
            }

            if (!found) {
                response.put("error_project_" + projectId, "Project not found");
                anyError = true;
            }
        }

        response.put("status", "votes updated");

        if (anyError) {
            return ResponseEntity.status(HttpStatus.PARTIAL_CONTENT).body(response); // 206
        } else {
            return ResponseEntity.ok(response); // 200 OK
        }
    }

    @PostMapping("/authorize")
    public ResponseEntity<Map<String, Object>> authorize(@RequestBody Map<String, String> request) {
        String rfid = request.get("rfid");
        Map<String, Object> response = new HashMap<>();

        if (rfid == null || rfid.isEmpty()) {
            response.put("message", "No RFID provided");
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(response); // 400
        }

        if (authorizedRfids.contains(rfid)) {
            response.put("message", "Authorized");
            return ResponseEntity.ok(response); // 200 OK
        } else {
            response.put("message", "Forbidden");
            return ResponseEntity.status(HttpStatus.FORBIDDEN).body(response); // 403
        }
    }
}
